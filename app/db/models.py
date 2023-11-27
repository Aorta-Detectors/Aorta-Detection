from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    second_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)

    appointment_user_link = relationship("Appointment", back_populates="user")


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, unique=True)
    full_name = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    is_male = Column(Boolean, nullable=False)

    height = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=False)

    examination_patient_link = relationship(
        "Examination", back_populates="patient"
    )


class Examination(Base):
    __tablename__ = "examinations"

    examination_id = Column(Integer, primary_key=True, unique=True)

    patient_id = Column(
        Integer,
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_id = Column(Integer)
    created_at = Column(DateTime)

    patient = relationship(
        "Patient", back_populates="examination_patient_link"
    )
    examination_appointment_link = relationship(
        "Appointment", back_populates="examination"
    )


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, index=True)
    appointment_time = Column(DateTime, nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    examination_id = Column(
        Integer,
        ForeignKey("examinations.examination_id", ondelete="CASCADE"),
        nullable=False,
    )

    examination = relationship(
        "Examination", back_populates="examination_appointment_link"
    )
    user = relationship("User", back_populates="appointment_user_link")

    file_appointment_link = relationship(
        "AppointmentFile", back_populates="appointment_file_link"
    )

    blood_pressure = Column(String)
    pulse = Column(Integer)
    swell = Column(String)
    complains = Column(Text)
    diagnosis = Column(Text)
    disease_complications = Column(Text)
    comorbidities = Column(Text)
    disease_anamnesis = Column(Text)
    life_anamnesis = Column(Text)
    echocardiogram_data = Column(Text)
    is_ready = Column(Boolean)


class AppointmentFile(Base):
    __tablename__ = "appointment_file"
    appointment_file_key = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(
        Integer,
        ForeignKey("appointments.appointment_id", ondelete="CASCADE"),
        nullable=False,
    )

    appointment_file_link = relationship(
        "Appointment", back_populates="file_appointment_link"
    )
    file_hash = Column(String)


class Series(Base):
    __tablename__ = "series"
    series_hash = Column(String, primary_key=True, index=True)
    file_hash = Column(String)
    status = Column(String)
