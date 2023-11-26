import inspect
from datetime import date, datetime
from typing import List, Optional, Type

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
    patient_id: str
    full_name: str
    birth_date: date
    is_male: bool
    height: int
    weight: int

    class Config:
        orm_mode = True


@as_form
class InputAppointment(BaseModel):
    blood_pressure: Optional[str] = None
    pulse: Optional[int] = None
    swell: Optional[str] = None
    complains: Optional[str] = None
    diagnosis: Optional[str] = None
    disease_complications: Optional[str] = None
    comorbidities: Optional[str] = None
    disease_anamnesis: Optional[str] = None
    life_anamnesis: Optional[str] = None
    echocardiogram_data: Optional[str] = None

    class Config:
        orm_mode = True


class Appointment(BaseModel):
    user_id: int
    examination_id: int

    appointment_time: datetime

    blood_pressure: Optional[str] = None
    pulse: Optional[int] = None
    swell: Optional[str] = None
    complains: Optional[str] = None
    diagnosis: Optional[str] = None
    disease_complications: Optional[str] = None
    comorbidities: Optional[str] = None
    disease_anamnesis: Optional[str] = None
    life_anamnesis: Optional[str] = None
    echocardiogram_data: Optional[str] = None
    is_ready: bool = False

    class Config:
        orm_mode = True


class ResponseAppointment(Appointment):
    appointment_id: int


@as_form
class InputExamination(InputAppointment):
    patient_id: str
    full_name: str
    birth_date: date
    is_male: bool
    height: int
    weight: int

    class Config:
        orm_mode = True


class Examination(BaseModel):
    patient_id: int
    creator_id: int
    created_at: datetime

    class Config:
        orm_mode = True


class ResponseExamination(Examination):
    examination_id: int
    patient: Patient
    appointments: List[ResponseAppointment]


class ResponseExaminationGeneral(BaseModel):
    examination_id: int
    patient_id: str
    patient_name: str
    last_appointment_time: datetime


class ResponseExaminationsPagination(BaseModel):
    current_page: int
    objects_count_on_current_page: int
    objects_count_total: int
    page_total_count: int
    requested_examinations: List[ResponseExaminationGeneral]


class ResponsePatientsPagination(BaseModel):
    current_page: int
    objects_count_on_current_page: int
    objects_count_total: int
    page_total_count: int
    requested_patients: List[Patient]


class StatusInput(BaseModel):
    appointment_id: int
    file_hash: str
    series_hashes: List[str]


class StepStatus(BaseModel):
    step_name: str
    is_ready: bool


class SeriesStepsStatuses(BaseModel):
    series_hash: str
    series_statuses: List[StepStatus]


class ResponseSeriesesStatuses(BaseModel):
    serieses_num: int
    file_hash: str
    serieses_statuses: List[SeriesStepsStatuses]


class StatusChange(BaseModel):
    file_hash: str
    series_hash: str
    status: str
