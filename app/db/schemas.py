from datetime import date, datetime

from fastapi import Form
from pydantic import BaseModel


class User(BaseModel):
    first_name: str
    second_name: str
    email: str
    password: str
    role: str

    class Config:
        orm_mode = True


class LoginUser(BaseModel):
    email: str
    password: str

    class Config:
        orm_mode = True


class ResponseUser(BaseModel):
    user_id: int
    first_name: str
    second_name: str
    email: str
    role: str

    class Config:
        orm_mode = True


class Patient(BaseModel):
    patient_id: int
    full_name: str
    birth_date: date
    is_male: bool

    class Config:
        orm_mode = True


class InputAppointment(BaseModel):
    patient_id: int = Form(...)
    full_name: str = Form(...)
    birth_date: date = Form(...)
    is_male: bool = Form(...)

    blood_pressure: str = Form(...)
    pulse: int = Form(...)
    swell: str = Form(...)
    complains: str = Form(...)
    diagnosis: str = Form(...)
    disease_complications: str = Form(...)
    comorbidities: str = Form(...)
    disease_anamnesis: str = Form(...)
    life_anamnesis: str = Form(...)
    echocardiogram_data: str = Form(...)

    class Config:
        orm_mode = True


class Appointment(BaseModel):
    user_id: int
    patient_id: int

    appointment_time: datetime

    blood_pressure: str
    pulse: int
    swell: str
    complains: str
    diagnosis: str
    disease_complications: str
    comorbidities: str
    disease_anamnesis: str
    life_anamnesis: str
    echocardiogram_data: str
    is_ready: bool = False

    class Config:
        orm_mode = True


class ResponseAppointment(BaseModel):
    appointment_id: int
    full_name: str
    appointment_time: datetime
    is_ready: bool

    class Config:
        orm_mode = True
