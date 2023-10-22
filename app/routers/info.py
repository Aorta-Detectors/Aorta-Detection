from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import oauth2
from app.db import crud, schemas
from app.db.database import get_db

router = APIRouter()


@router.get("/me", response_model=schemas.ResponseUser)
def get_me(
    db: Session = Depends(get_db), user_id: str = Depends(oauth2.require_user)
):
    user = crud.get_user_by_id(db, int(user_id))
    return user
