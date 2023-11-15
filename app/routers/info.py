from datetime import datetime
from typing import List, Optional

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
from app.db import crud, schemas
from app.db.database import get_db, get_minio_db

router = APIRouter()


@router.get("/me", response_model=schemas.ResponseUser)
def get_me(
    db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)
):
    user = crud.get_user_by_id(db, int(user_id))
    return user


@router.get("/get_patient", response_model=schemas.Patient)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
):
    patient = crud.get_patient_by_id(db, int(patient_id))
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
    appointment_updated = crud.create_appointment(db, appointment)
    result = {"appointment_id": appointment_updated.appointment_id}
    if file is not None:
        new_filename = (
            str(appointment_updated.appointment_id)
            + "."
            + file.filename.split(".")[-1]
        )

        file_data = file.file.read()
        file_length = len(file_data)
        file.file.seek(0)
        minio_db.put_object(
            "input", new_filename, data=file.file, length=file_length
        )
        result["filename"] = new_filename
    return result


@router.post("/create_examination", response_model=schemas.ResponseExamination)
def create_examination(
    examination_data: schemas.InputExamination = Depends(
        schemas.InputExamination.as_form
    ),
    file: Optional[UploadFile] = None,
    db: Session = Depends(get_db),
    minio_db: Minio = Depends(get_minio_db),
    user_id: str = Depends(oauth2.require_user),
):
    patient = crud.get_patient_by_id(db, examination_data.patient_id)
    if not patient:
        patient = schemas.Patient(**examination_data.dict())
        patient = crud.create_patient(db, patient)
    examination = schemas.Examination(**examination_data.dict())
    examination_updated = crud.create_examination(db, examination)

    appointment = schemas.Appointment(
        user_id=user_id,
        appointment_time=datetime.now(),
        examination_id=examination_updated.examination_id,
        **examination_data.dict(),
    )
    appointment_info = _add_appointment(appointment, db, minio_db, file)
    response = schemas.ResponseExamination(
        patient_id=examination_updated.patient_id,
        examination_id=examination_updated.examination_id,
        appointment_ids=[appointment_info["appointment_id"]],
    )

    return response


@router.get("/get_examination", response_model=schemas.ResponseExamination)
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
    response = schemas.ResponseExamination(
        patient_id=query_result[0][0].patient_id,
        examination_id=examination_id,
        appointment_ids=[app.appointment_id for _, app in query_result],
    )
    return response


@router.get(
    "/get_examinations",
    response_model=List[schemas.ResponseExaminationGeneral],
)
def get_examinations(
    page: int = Query(ge=0, default=0),
    size: int = Query(ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    query_result = crud.get_examinations(
        db, int(user_id), page=page, page_size=size
    )
    response = []
    for exam_id, pat_id, pat_name, app_time in query_result:
        response.append(
            schemas.ResponseExaminationGeneral(
                examination_id=exam_id,
                patient_id=pat_id,
                patient_name=pat_name,
                last_appointment_time=app_time,
            )
        )
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


@router.put("/add_appointment")
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
    appointment = schemas.Appointment(
        user_id=user_id,
        appointment_time=datetime.now(),
        examination_id=examination_id,
        **appointment_data.dict(),
    )
    response = _add_appointment(appointment, db, minio_db, file)

    return response


@router.get("/get_appointment", response_model=schemas.ResponseAppointment)
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

@router.get("/general_patients_info", response_model=List[schemas.Patient])
def general_patients_info(
    db: Session = Depends(get_db), 
    user_id: str = Depends(oauth2.require_user),
):
    patients = crud.get_all_user_patients(db, int(user_id))
    return patients

@router.get("/patients_page", response_model=List[schemas.Patient])
def patients_page(
    page: int = Query(ge=0, default=0),
    size: int = Query(ge=1, le=100),
    db: Session = Depends(get_db), 
    user_id: str = Depends(oauth2.require_user),
):
    patients = crud.get_all_user_patients(db, int(user_id))
    offset = page * size
    return patients[offset:offset+size]
