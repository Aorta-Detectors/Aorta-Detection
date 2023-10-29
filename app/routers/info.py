import tempfile
from datetime import datetime
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from minio import Minio
from sqlalchemy.orm import Session

from app import oauth2
from app.db import crud, models, schemas
from app.db.database import get_db, get_minio_db

router = APIRouter()


@router.get("/me", response_model=schemas.ResponseUser)
def get_me(
    db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)
):
    user = crud.get_user_by_id(db, int(user_id))
    return user


@router.post("/create_appointment")
def create_appointment(
    appointment_data: schemas.InputAppointment = Depends(),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    minio_db: Minio = Depends(get_minio_db),
    user_id: str = Depends(oauth2.require_user),
):
    patient = crud.get_patient_by_id(db, appointment_data.patient_id)
    if not patient:
        patient = schemas.Patient(**appointment_data.dict())
        patient = crud.create_patient(db, patient)

    appointment = schemas.Appointment(
        user_id=user_id,
        appointment_time=datetime.now(),
        **appointment_data.dict(),
    )
    appointment_updated = crud.create_appointment(db, appointment)
    new_filename = (
        str(appointment_updated.appointment_id)
        + "."
        + file.filename.split(".")[-1]
    )

    temp_dir = tempfile.TemporaryDirectory()
    file_path = f"./{temp_dir.name}/{new_filename}"

    with open(file_path, "wb+") as f:
        f.write(file.file.read())
    minio_db.fput_object("input", new_filename, file_path)
    temp_dir.cleanup()

    return {"status": "success"}


def create_response(appointment: models.Appointment, patient: models.Patient):
    return {
        "appointment_id": appointment.appointment_id,
        "full_name": patient.full_name,
        "appointment_time": appointment.appointment_time,
        "is_ready": appointment.is_ready,
    }


@router.get("/general_info", response_model=List[schemas.ResponseAppointment])
def general_appointment_info(
    db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)
):
    app_pat_info = crud.get_appointment(db, int(user_id), page=0, page_size=10)
    gen_info = [create_response(app, pat) for app, pat in app_pat_info]
    return gen_info


@router.get(
    "/appointments_page", response_model=List[schemas.ResponseAppointment]
)
def appointment_page(
    page: int = Query(ge=0, default=0),
    size: int = Query(ge=1, le=100),
    db: Session = Depends(get_db),
    user_id: str = Depends(oauth2.require_user),
):
    app_pat_info = crud.get_appointment(
        db, int(user_id), page=page, page_size=size
    )
    gen_info = [create_response(app, pat) for app, pat in app_pat_info]
    return gen_info


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
