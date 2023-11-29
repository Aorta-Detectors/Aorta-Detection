import os
import tempfile
import zipfile
from datetime import datetime
from math import ceil

import cv2
import matplotlib.pyplot as plt
import numpy as np
import requests
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from minio import Minio
from PIL import Image
from sqlalchemy.orm import Session

from app import oauth2
from app.config import settings
from app.db import crud, schemas
from app.db.database import get_db, get_minio_db, get_minio_results
from dicom_wrapper import DicomCube, DicomParser
from minio_path.utils import numpy_load

router = APIRouter()
AI_MODULE_HTTP = settings.AI_MODULE_HTTP
AI_MODULE_POST_ENDPOINT = settings.AI_MODULE_POST_ENDPOINT


@router.get("/me", response_model=schemas.ResponseUser)
def get_me(
    db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)
):
    user = crud.get_user_by_id(db, int(user_id))
    return user


@router.get(
    "/get_patient",
    response_model=schemas.Patient,
    description="Get information about the patient by his id.",
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
):
    patient = crud.get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient with given id not found",
        )
    return patient


@router.post(
    "/create_examination",
    response_model=schemas.ResponseExamination,
    description="""
Create a new medical examination.
It is necessary to fill in the user information.
You also need to fill out exactly 1 appointment.
""",
)
def create_examination(
    examination_data: schemas.InputExamination = Depends(
        schemas.InputExamination.as_form
    ),
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    patient_db = crud.get_patient_by_id(db, examination_data.patient_id)
    if not patient_db:
        patient = schemas.Patient(**examination_data.dict())
        patient_db = crud.create_patient(db, patient)
    patient_updated = schemas.Patient(**patient_db.__dict__)

    created_at = datetime.now()
    examination = schemas.Examination(
        creator_id=int(user_id),
        created_at=created_at,
        **examination_data.dict(),
    )
    examination_db = crud.create_examination(db, examination)

    appointment = schemas.Appointment(
        user_id=user_id,
        appointment_time=datetime.now(),
        examination_id=examination_db.examination_id,
        **examination_data.dict(),
    )
    appointment_db = crud.create_appointment(db, appointment)
    appointment_updated = schemas.ResponseAppointment(
        **appointment_db.__dict__
    )

    response = schemas.ResponseExamination(
        examination_id=examination_db.examination_id,
        **examination.dict(),
        patient=patient_updated,
        appointments=[appointment_updated],
    )

    return response


@router.get(
    "/get_examination",
    response_model=schemas.ResponseExamination,
    description="Get all the information about the survey by its id.",
)
def get_examination(
    examination_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    query_result = crud.get_examination_by_id(db, examination_id)
    if not query_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Examination with given id not found",
        )
    patient = schemas.Patient(**query_result[0][2].__dict__)
    response = schemas.ResponseExamination(
        **query_result[0][0].__dict__,
        patient=patient,
        appointments=[
            schemas.ResponseAppointment(**app.__dict__)
            for _, app, _ in query_result
        ],
    )
    return response


@router.get(
    "/get_examinations",
    response_model=schemas.ResponseExaminationsPagination,
    description="""
Get a list of examinations in which the
current user (doctor) participated.
""",
)
def get_examinations(
    page: int = Query(ge=1, default=1),
    size: int = Query(ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    query_result = crud.get_examinations(
        db, int(user_id), page=page - 1, page_size=size
    )
    all_examinations = crud.get_examinations(
        db,
        int(user_id),
        page=0,
        page_size=int(1e15),
    )

    requested_examinations = []
    for exam_id, pat_id, pat_name, app_time in query_result:
        requested_examinations.append(
            schemas.ResponseExaminationGeneral(
                examination_id=exam_id,
                patient_id=pat_id,
                patient_name=pat_name,
                last_appointment_time=app_time,
            )
        )
    response = {
        "current_page": page,
        "objects_count_on_current_page": len(query_result),
        "objects_count_total": len(all_examinations),
        "page_total_count": ceil(len(all_examinations) / size),
        "requested_examinations": requested_examinations,
    }
    return response


@router.delete("/delete_examination", status_code=status.HTTP_200_OK)
def delete_examination(
    examination_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    examination = crud.get_examination_by_id(db, examination_id)
    if not examination:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Examination already deleted",
        )
    crud.delete_examination_by_id(db, examination_id)

    return {"status": "success"}


@router.put(
    "/add_appointment",
    description="Add another appointment to the existing examination.",
)
def add_appointment(
    examination_id: int,
    appointment_data: schemas.InputAppointment = Depends(
        schemas.InputAppointment.as_form
    ),
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    examination = crud.get_examination_by_id(db, examination_id)
    if not examination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Examination is not exists",
        )
    appointment = schemas.Appointment(
        user_id=user_id,
        appointment_time=datetime.now(),
        examination_id=examination_id,
        **appointment_data.dict(),
    )
    response = crud.create_appointment(db, appointment)

    return response


@router.put(
    "/add_file",
    response_model=schemas.ResponseSeriesesStatuses,
    description="Add file to existing appointment.",
)
def add_file(
    appointment_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    s3_path: Minio = Depends(get_minio_db),
    user_id: str = Depends(oauth2.require_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} is not exists",
        )
    file_ext = file.filename.split(".")[-1]
    if file_ext != "zip":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only zip files are supported",
        )
    dicom_unzip = zipfile.ZipFile(file.file)

    for filename in dicom_unzip.namelist():
        (s3_path / filename).write(
            dicom_unzip.open(filename), len(dicom_unzip.open(filename).read())
        )
        if "DICOMDIR" in filename:
            dicom_path = s3_path.joinpath(*filename.split("/"))

    cube = DicomCube(DicomParser(dicom_path))
    dicom_path = cube.upload(s3_path)
    file_hash = cube.hash

    ai_module_request = {
        "s3_dicom_path": file_hash,
        "slice_num": 10,
    }

    possible_steps = [
        "Preprocessing",
        "Segmentation",
        "Resampling",
        "Pathline extraction",
        "Slicing",
    ]
    serieses_hashes, serieses_statuses = [], []
    for series_hash, series_data in cube.serieses:
        if len(series_data) == 0:
            continue
        serieses_hashes.append(series_hash)
        series_steps_statuses = []
        for step_name in possible_steps:
            step_status = schemas.StepStatus(
                step_name=step_name,
                is_ready=False,
            )
            series_steps_statuses.append(step_status)

        series_steps_statuses = schemas.SeriesStepsStatuses(
            series_hash=series_hash,
            series_statuses=series_steps_statuses,
        )
        serieses_statuses.append(series_steps_statuses)
    response = schemas.ResponseSeriesesStatuses(
        serieses_num=len(serieses_hashes),
        file_hash=file_hash,
        serieses_statuses=serieses_statuses,
    )
    input_data = schemas.StatusInput(
        appointment_id=appointment_id,
        file_hash=file_hash,
        series_hashes=serieses_hashes,
    )
    crud.create_status(db, input_data)

    try:
        ai_response = requests.post(
            f"{AI_MODULE_HTTP}{AI_MODULE_POST_ENDPOINT}",
            json=ai_module_request,
        )
        # Check if the request was successful (status code 2xx)
        ai_response.raise_for_status()
    except requests.HTTPError as exc:
        # Handle any HTTP errors
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        )

    return response


@router.get(
    "/get_status",
    response_model=schemas.ResponseSeriesesStatuses,
    description="Get current status for appointment file.",
)
def get_status(
    appointment_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment {appointment_id} is not exists",
        )
    possible_steps = [
        "Preprocessing",
        "Segmentation",
        "Resampling",
        "Pathline extraction",
        "Slicing",
        "Done",
    ]
    serieses_statuses = []
    file_series = crud.get_status(db, appointment_id)
    for _, series in file_series:
        file_hash = series.file_hash
        series_hash = series.series_hash
        series_status = series.status

        is_failed = False
        if series_status.startswith("Failed "):
            is_failed = True
            series_status = series_status.replace("Failed ", "")

        is_ready_until = possible_steps.index(series_status)
        series_steps_statuses = []

        for i, step_name in enumerate(possible_steps[:-1]):
            step_status = schemas.StepStatus(
                step_name=step_name,
                is_ready=True if i < is_ready_until else False,
                is_failed=False if i < is_ready_until else is_failed,
            )
            series_steps_statuses.append(step_status)
        series_steps_statuses = schemas.SeriesStepsStatuses(
            series_hash=series_hash,
            series_statuses=series_steps_statuses,
        )
        serieses_statuses.append(series_steps_statuses)
    response = schemas.ResponseSeriesesStatuses(
        serieses_num=len(file_series),
        file_hash=file_hash,
        serieses_statuses=serieses_statuses,
    )
    return response


@router.get(
    "/get_slices_num",
    description="Get num of slices for report.",
)
def get_slices_num(
    appointment_id: int,
    series_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    return {"slices_num": 10}


def get_temp_dir():
    dir = tempfile.TemporaryDirectory()
    try:
        yield dir.name
    finally:
        del dir


@router.get(
    "/get_slice",
    description="Get #slice_num slice for report.",
)
def get_slice(
    appointment_id: int,
    series_id: int,
    slice_num: int,
    db: Session = Depends(get_db),
    minio: Minio = Depends(get_minio_results),
    temp_dir=Depends(get_temp_dir),
    user_id: str = Depends(oauth2.require_user),
):
    statuses = crud.get_status(db, appointment_id)
    series = statuses[series_id][1]
    file_hash = series.file_hash
    series_hash = series.series_hash

    path = minio / file_hash / series_hash / "slices" / str(slice_num)
    slice = numpy_load(path / "slice.npy")
    slice = (slice - slice.min()) / (slice.max() - slice.min())
    slice = (slice * 255).astype(np.uint8)
    gray_image = Image.fromarray(slice, "L")

    temp_file_path = os.path.join(temp_dir, "temp_image.png")
    gray_image.save(temp_file_path)

    return FileResponse(temp_file_path)


@router.get(
    "/get_rotated_slice_masked",
    description="Get #slice_num rotated slice with "
    "aorta mask on it for report.",
)
def get_rotated_slice_masked(
    appointment_id: int,
    series_id: int,
    slice_num: int,
    db: Session = Depends(get_db),
    minio: Minio = Depends(get_minio_results),
    temp_dir=Depends(get_temp_dir),
    user_id: str = Depends(oauth2.require_user),
):
    statuses = crud.get_status(db, appointment_id)
    series = statuses[series_id][1]
    file_hash = series.file_hash
    series_hash = series.series_hash

    path = minio / file_hash / series_hash / "slices" / str(slice_num)
    orig_slice = numpy_load(path / "slice.npy")
    orig_slice = (orig_slice - orig_slice.min()) / (
        orig_slice.max() - orig_slice.min()
    )
    orig_slice = (orig_slice * 255).astype(np.uint8)

    rot_slice = numpy_load(path / "rotated_slice.npy")
    rot_slice = (rot_slice - rot_slice.min()) / (
        rot_slice.max() - rot_slice.min()
    )
    rot_slice = (rot_slice * 255).astype(np.uint8)
    first_nonzero_row = rot_slice.nonzero()[0][0]
    last_nonzero_row = rot_slice.nonzero()[0][-1]
    rot_slice = rot_slice[first_nonzero_row:last_nonzero_row, :]

    mask = numpy_load(path / "rotated_mask.npy").astype(np.uint8) * 255
    mask = mask[first_nonzero_row:last_nonzero_row, :]

    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    rot_slice = cv2.cvtColor(rot_slice, cv2.COLOR_GRAY2RGB)
    cv2.drawContours(rot_slice, contours, -1, (255, 255, 0), 1)

    temp_file_path = os.path.join(temp_dir, "temp_image.png")

    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    ax = ax.ravel()
    ax[0].imshow(orig_slice, "gray")
    ax[0].axis("off")
    ax[1].imshow(rot_slice)
    ax[1].axis("off")
    fig.tight_layout()
    fig.savefig(temp_file_path)

    return FileResponse(temp_file_path)


@router.get(
    "/get_slice_diameter", description="Get slice diameter in millimeters."
)
def get_diameter(
    appointment_id: int,
    series_id: int,
    slice_num: int,
    user_id: str = Depends(oauth2.require_user),
):
    return {"diameter": 25}


@router.get(
    "/get_appointment",
    response_model=schemas.ResponseAppointment,
    description="Get information about the appointment by its id.",
)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment with given id not found",
        )
    return appointment


@router.delete("/delete_appointment", status_code=status.HTTP_200_OK)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    appointment = crud.get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment already deleted",
        )
    crud.delete_appointment_by_id(db, appointment_id)
    return {"status": "success"}


@router.get(
    "/patients_page",
    response_model=schemas.ResponsePatientsPagination,
    description="Get a page with patients who have been to see this doctor.",
)
def patients_page(
    page: int = Query(ge=1, default=1),
    size: int = Query(ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    patients = crud.get_all_user_patients(db, int(user_id))
    offset = (page - 1) * size
    requested_patients = patients[offset : offset + size]
    response = {
        "current_page": page,
        "objects_count_on_current_page": len(requested_patients),
        "objects_count_total": len(patients),
        "page_total_count": ceil(len(patients) / size),
        "requested_patients": requested_patients,
    }
    return response
