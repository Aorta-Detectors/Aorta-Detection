from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings
from minio_path import MinioPath

USER = settings.POSTGRES_USER
PASS = settings.POSTGRES_PASSWORD
HOST = settings.POSTGRES_HOST
PORT = settings.POSTGRES_PORT
NAME = settings.POSTGRES_DB

SQLALCHEMY_DATABASE_URL = f"postgresql://{USER}:{PASS}@{HOST}:{PORT}/{NAME}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


MINIO_HTTP = settings.MINIO_HTTP
MINIO_ACCESS_KEY = settings.MINIO_ROOT_USER
MINIO_SECRET_KEY = settings.MINIO_ROOT_PASSWORD


def get_minio_db():
    s3_path = (
        MinioPath.fromauth(
            host=MINIO_HTTP,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )
        / "inputdicom"
    )
    try:
        yield s3_path
    finally:
        del s3_path
