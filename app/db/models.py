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

    appointment_patient_link = relationship(
        "Appointment", back_populates="patient"
    )


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, index=True)
    appointment_time = Column(DateTime, nullable=False)
    patient_id = Column(
        Integer,
        ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    user = relationship("User", back_populates="appointment_user_link")
    patient = relationship(
        "Patient", back_populates="appointment_patient_link"
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
