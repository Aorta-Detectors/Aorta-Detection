from pydantic import BaseModel

class User(BaseModel):
    first_name: str
    second_name: str
    email: str
    password: str
    role: str

    class Config:
        orm_mode = True