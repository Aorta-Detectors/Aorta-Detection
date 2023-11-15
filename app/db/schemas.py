import inspect
from datetime import date, datetime
from typing import List, Type

from fastapi import Form
from pydantic import BaseModel
from pydantic.fields import ModelField


def as_form(cls: Type[BaseModel]):
    new_parameters = []

    for _, model_field in cls.__fields__.items():
        model_field: ModelField  # type: ignore

        new_parameters.append(
            inspect.Parameter(
                model_field.alias,
                inspect.Parameter.POSITIONAL_ONLY,
                default=Form(...)
                if model_field.required
                else Form(model_field.default),
                annotation=model_field.outer_type_,
            )
        )

    async def as_form_func(**data):
        return cls(**data)

    sig = inspect.signature(as_form_func)
    sig = sig.replace(parameters=new_parameters)
    as_form_func.__signature__ = sig  # type: ignore
    setattr(cls, "as_form", as_form_func)
    return cls


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
    height: int
    weight: int

    class Config:
        orm_mode = True


@as_form
class InputAppointment(BaseModel):
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

    class Config:
        orm_mode = True


class Appointment(BaseModel):
    user_id: int
    examination_id: int

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


class ResponseAppointment(Appointment):
    appointment_id: int


@as_form
class InputExamination(InputAppointment):
    patient_id: int
    full_name: str
    birth_date: date
    is_male: bool
    height: int
    weight: int

    class Config:
        orm_mode = True


class Examination(BaseModel):
    patient_id: int

    class Config:
        orm_mode = True


class ResponseExamination(Examination):
    examination_id: int
    appointment_ids: List[int]


class ResponseExaminationGeneral(BaseModel):
    examination_id: int
    patient_id: int
    patient_name: str
    last_appointment_time: datetime
