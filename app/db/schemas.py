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
