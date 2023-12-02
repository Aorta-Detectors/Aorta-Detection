from sqlalchemy import desc, func
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


def create_patient(db: Session, patient: schemas.Patient):
    db_patient = models.Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


def get_patient_by_id(db: Session, patient_id: str):
    return (
        db.query(models.Patient)
        .filter(models.Patient.patient_id == patient_id)
        .first()
    )


def delete_patient_by_id(db: Session, patient_id: str):
    db.query(models.Patient).filter(
        models.Patient.patient_id == patient_id
    ).delete()
    db.commit()
    return {"status": 0}


def create_examination(db: Session, examination: schemas.Examination):
    db_examination = models.Examination(**examination.dict())
    db.add(db_examination)
    db.commit()
    db.refresh(db_examination)
    return db_examination


def get_examinations(db: Session, user_id: int, page: int, page_size: int):
    offset = page * page_size
    limit = page_size
    subquery_max_time = (
        db.query(
            models.Appointment.examination_id,
            func.max(models.Appointment.appointment_time).label("max_time"),
        )
        .group_by(models.Appointment.examination_id)
        .subquery()
    )

    subquery_appointments = (
        db.query(models.Appointment.examination_id)
        .filter(models.Appointment.user_id == user_id)
        .distinct()
        .subquery()
    )

    query = (
        db.query(
            models.Examination.examination_id,
            models.Patient.patient_id,
            models.Patient.full_name,
            subquery_max_time.c.max_time,
        )
        .join(
            subquery_appointments,
            models.Examination.examination_id
            == subquery_appointments.c.examination_id,
        )
        .join(
            subquery_max_time,
            models.Examination.examination_id
            == subquery_max_time.c.examination_id,
        )
        .join(
            models.Patient,
            models.Examination.patient_id == models.Patient.patient_id,
        )
        .distinct()
        .order_by(desc(subquery_max_time.c.max_time))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return query


def get_examination_by_id(db: Session, examination_id: int):
    result = (
        db.query(models.Examination, models.Appointment, models.Patient)
        .join(
            models.Appointment,
            models.Examination.examination_id
            == models.Appointment.examination_id,
        )
        .join(
            models.Patient,
            models.Examination.patient_id == models.Patient.patient_id,
        )
        .filter(models.Examination.examination_id == examination_id)
        .order_by(models.Appointment.appointment_time)
        .all()
    )
    return result


def get_all_user_patients(db: Session, user_id: int):
    unique_examination_ids = (
        db.query(models.Appointment.examination_id)
        .filter(models.Appointment.user_id == user_id)
        .distinct()
        .subquery()
    )

    unique_patient_ids = (
        db.query(models.Examination.patient_id)
        .filter(models.Examination.examination_id.in_(unique_examination_ids))
        .distinct()
        .subquery()
    )

    unique_patients = (
        db.query(models.Patient)
        .filter(models.Patient.patient_id.in_(unique_patient_ids))
        .distinct()
        .all()
    )

    return unique_patients


def delete_examination_by_id(db: Session, examination_id: int):
    db.query(models.Examination).filter(
        models.Examination.examination_id == examination_id
    ).delete()
    db.commit()
    return {"status": 0}


def create_appointment(db: Session, appointment: schemas.Appointment):
    db_appointment = models.Appointment(**appointment.dict())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def get_appointment_by_id(db: Session, appointment_id: int):
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.appointment_id == appointment_id)
        .first()
    )


def update_appointment(
    db: Session, appointment_id, appointment: schemas.Appointment
):
    db_appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.appointment_id == appointment_id)
        .first()
    )

    for key, value in appointment.dict().items():
        setattr(db_appointment, key, value) if value is not None else None

    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def delete_appointment_by_id(db: Session, appointment_id: int):
    db.query(models.Appointment).filter(
        models.Appointment.appointment_id == appointment_id
    ).delete()
    db.commit()
    return {"status": 0}


def create_status(db: Session, input_data: schemas.StatusInput):
    db_appointment_file = models.AppointmentFile(
        appointment_id=input_data.appointment_id,
        file_hash=input_data.file_hash,
    )
    existing_appointment_file = (
        db.query(models.AppointmentFile)
        .filter_by(appointment_id=input_data.appointment_id)
        .first()
    )
    if existing_appointment_file:
        existing_appointment_file.file_hash = input_data.file_hash
        db.commit()
    else:
        db.add(db_appointment_file)
        db.commit()
        db.refresh(db_appointment_file)

    for series_hash in sorted(input_data.series_hashes):
        db_series = models.Series(
            series_hash=series_hash,
            file_hash=input_data.file_hash,
            status="Preprocessing",
        )
        existing_series = (
            db.query(models.Series)
            .filter_by(series_hash=series_hash, file_hash=input_data.file_hash)
            .first()
        )
        if not existing_series:
            db.add(db_series)
            db.commit()
    return db_appointment_file


def get_series_status(db: Session, file_hash: str, series_hash: str):
    result = (
        db.query(models.Series)
        .filter(
            (models.Series.series_hash == series_hash)
            & (models.Series.file_hash == file_hash)
        )
        .first()
    )
    return result


def check_if_all_series_done(db: Session, file_hash: str):
    result = (
        db.query(models.Series)
        .filter(models.Series.file_hash == file_hash)
        .order_by(models.Series.series_hash)
        .all()
    )
    for series in result:
        if series.status != "Done":
            return False
    return True


def change_status(db: Session, data: schemas.StatusChange):
    result = (
        db.query(models.Series)
        .filter(models.Series.file_hash == data.file_hash)
        .filter(models.Series.series_hash == data.series_hash)
        .first()
    )
    possible_steps = [
        "Preprocessing",
        "Segmentation",
        "Resampling",
        "Pathline extraction",
        "Slicing",
        "Done",
    ]
    index_current = possible_steps.index(result.status.replace("Failed ", ""))
    index_new = possible_steps.index(data.status.replace("Failed ", ""))
    if index_current <= index_new:
        result.status = data.status
        db.commit()
        if data.status == "Done":
            is_all_series_done = check_if_all_series_done(db, data.file_hash)
            if is_all_series_done:
                appointment_file = get_appointment_by_file(db, data.file_hash)
                appointment_id = appointment_file.appointment_id
                appointment = get_appointment_by_id(db, appointment_id)
                appointment.is_ready = True
                db.commit()
                db.refresh(appointment)
    db.refresh(result)
    return result


def get_appointment_by_file(db: Session, file_hash: str):
    result = (
        db.query(models.AppointmentFile)
        .filter(models.AppointmentFile.file_hash == file_hash)
        .order_by(models.AppointmentFile.appointment_file_key.desc())
        .first()
    )
    return result


def get_status(db: Session, appointment_id: int):
    result = (
        db.query(models.AppointmentFile, models.Series)
        .join(
            models.Series,
            models.AppointmentFile.file_hash == models.Series.file_hash,
        )
        .filter(models.AppointmentFile.appointment_id == appointment_id)
        .order_by(models.Series.series_hash)
        .all()
    )
    return result
