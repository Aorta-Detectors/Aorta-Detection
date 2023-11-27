from pydantic import BaseModel


class MinioConfig(BaseModel):
    """Config minio access."""

    host: str
    access_key: str
    secret_key: str
    secure: bool = False
