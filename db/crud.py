from sqlalchemy.orm import Session

from . import models, schemas


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.User):
    db_user = models.User(first_name = user.first_name,
                          second_name = user.second_name,
                          email = user.email,
                          password = user.password,
                          role = user.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user