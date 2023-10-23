from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

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
