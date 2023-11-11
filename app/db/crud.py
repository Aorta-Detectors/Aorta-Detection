from sqlalchemy import desc
from sqlalchemy.orm import Session

from . import models, schemas


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.User):
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_patient_by_id(db: Session, patient_id: int):
    return (
        db.query(models.Patient)
        .filter(models.Patient.patient_id == patient_id)
        .first()
    )


def create_patient(db: Session, patient: schemas.Patient):
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def get_appointment(db: Session, user_id: int, page: int, page_size: int):
    offset = page * page_size
    limit = page_size
    result = (
        db.query(models.Appointment, models.Patient)
        .join(
            models.Patient,
            models.Appointment.patient_id == models.Patient.patient_id,
        )
        .filter(models.Appointment.user_id == user_id)
        .order_by(desc(models.Appointment.appointment_time))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return result

def get_all_appointments(db: Session, user_id: int):
    result = (
        db.query(models.Appointment, models.Patient)
        .join(
            models.Patient,
            models.Appointment.patient_id == models.Patient.patient_id,
        )
        .filter(models.Appointment.user_id == user_id)
        .all()
    )
    return result


def get_appointment_by_id(db: Session, appointment_id: int):
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.appointment_id == appointment_id)
        .first()
    )


def create_appointment(db: Session, appointment: schemas.Appointment):
    db_appointment = models.Appointment(**appointment.dict())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def delete_appointment_by_id(db: Session, appointment_id: int):
    db.query(models.Appointment).filter(
        models.Appointment.appointment_id == appointment_id
    ).delete()
    db.commit()
    return {"status": 0}
