from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import crud, schemas
from app.db.database import get_db

router = APIRouter()


@router.put("/change_status", response_model=schemas.StatusChange)
def change_status(
    status_data: schemas.StatusChange, db: Session = Depends(get_db)
):
    changed_data = crud.change_status(db, status_data)
    return schemas.StatusChange(**changed_data.__dict__)
