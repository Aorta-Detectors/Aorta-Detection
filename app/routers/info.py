import zipfile
from datetime import datetime
from math import ceil
from typing import Optional

import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from minio import Minio
from sqlalchemy.orm import Session

from app import oauth2
from app.config import settings
from app.db import crud, schemas
from app.db.database import get_db, get_minio_db
from dicom_wrapper import DicomCube, DicomParser

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


def _add_appointment(
    appointment: schemas.Appointment,
    db: Session,
    minio_db: Minio,
    file: Optional[UploadFile] = None,
):
    appointment_db = crud.create_appointment(db, appointment)
    filename = None
    if file is not None:
        new_filename = (
            str(appointment_db.appointment_id)
            + "."
            + file.filename.split(".")[-1]
        )

        file_data = file.file.read()
        file_length = len(file_data)
        file.file.seek(0)
        minio_db.put_object(
            "input", new_filename, data=file.file, length=file_length
        )
    return appointment_db, filename


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
    file: Optional[UploadFile] = None,
    db: Session = Depends(get_db),
    minio_db: Minio = Depends(get_minio_db),
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
    appointment_db, _ = _add_appointment(appointment, db, minio_db, file)
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
    file: Optional[UploadFile] = None,
    db: Session = Depends(get_db),
    minio_db: Minio = Depends(get_minio_db),
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
    response = _add_appointment(appointment, db, minio_db, file)

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
        "s3_dicom_path": dicom_path.path,
    }

    try:
        with httpx.Client() as client:
            response = client.post(
                f"{AI_MODULE_HTTP}{AI_MODULE_POST_ENDPOINT}",
                json=ai_module_request,
            )
        # Check if the request was successful (status code 2xx)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # Handle any HTTP errors
        raise HTTPException(
            status_code=exc.response.status_code, detail=str(exc)
        )

    possible_steps = [
        "Preprocessing",
        "Segmentation",
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
        serieses_num=len(serieses_hashes), serieses_statuses=serieses_statuses
    )
    input_data = schemas.StatusInput(
        appointment_id=appointment_id,
        file_hash=file_hash,
        series_hashes=serieses_hashes,
    )
    crud.create_status(db, input_data)

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
    possible_steps = [
        "Preprocessing",
        "Segmentation",
        "Pathline extraction",
        "Slicing",
        "Done",
    ]
    serieses_statuses = []
    file_series = crud.get_status(db, appointment_id)
    for _, series in file_series:
        file_hash = series.file_hash
        series_hash = series.series_hash
        series_status = crud.get_series_status(
            db, file_hash, series_hash
        ).status
        is_ready_until = possible_steps.index(series_status)
        series_steps_statuses = []

        for i, step_name in enumerate(possible_steps[:-1]):
            step_status = schemas.StepStatus(
                step_name=step_name,
                is_ready=True if i < is_ready_until else False,
            )
            series_steps_statuses.append(step_status)
        series_steps_statuses = schemas.SeriesStepsStatuses(
            series_hash=series_hash,
            series_statuses=series_steps_statuses,
        )
        serieses_statuses.append(series_steps_statuses)
    response = schemas.ResponseSeriesesStatuses(
        serieses_num=len(file_series), serieses_statuses=serieses_statuses
    )
    return response


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
