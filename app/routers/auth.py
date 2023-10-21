from datetime import timedelta
from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import EmailStr

from app.db import schemas, crud
from app import utils
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.oauth2 import AuthJWT
from app.config import settings


router = APIRouter()
ACCESS_TOKEN_EXPIRES_IN = settings.ACCESS_TOKEN_EXPIRES_IN
REFRESH_TOKEN_EXPIRES_IN = settings.REFRESH_TOKEN_EXPIRES_IN


@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=schemas.ResponseUser)
async def create_user(payload: schemas.User, db: Session = Depends(get_db)):
    validated_email = EmailStr(payload.email.lower())
    user = crud.get_user_by_email(db, validated_email)
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail='Account already exist')
    payload.password = utils.hash_password(payload.password)
    payload.email = validated_email
    new_user = crud.create_user(db, payload)
    return new_user


@router.post('/login')
def login(payload: schemas.LoginUser, db: Session = Depends(get_db), Authorize: AuthJWT = Depends()):
    validated_email = EmailStr(payload.email.lower())
    user = crud.get_user_by_email(db, validated_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')

    if not utils.verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Incorrect Email or Password')

    access_token = Authorize.create_access_token(
        subject=str(user.user_id), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))

    refresh_token = Authorize.create_refresh_token(
        subject=str(user.user_id), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))

    Authorize.set_access_cookies(access_token)
    Authorize.set_refresh_cookies(refresh_token)

    return {'status': 'success', 
            'access_token': access_token, 
            'refresh_token': refresh_token}


@router.get('/refresh')
def refresh_token(Authorize: AuthJWT = Depends(), db: Session = Depends(get_db)):
    try:
        Authorize.jwt_refresh_token_required()

        user_id = Authorize.get_jwt_subject()
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not refresh access token')
        user = crud.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='The user belonging to this token no logger exist')
        access_token = Authorize.create_access_token(
            subject=str(user.user_id), expires_time=timedelta(minutes=ACCESS_TOKEN_EXPIRES_IN))
        refresh_token = Authorize.create_access_token(
            subject=str(user.user_id), expires_time=timedelta(minutes=REFRESH_TOKEN_EXPIRES_IN))
    except Exception as e:
        error = e.__class__.__name__
        if error == 'MissingTokenError':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='Please provide refresh token')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    Authorize.set_access_cookies(access_token)
    Authorize.set_refresh_cookies(refresh_token)
    return {'status': 'success', 
            'access_token': access_token, 
            'refresh_token': refresh_token}


@router.get('/logout', status_code=status.HTTP_200_OK)
def logout(Authorize: AuthJWT = Depends()):
    Authorize.unset_jwt_cookies()

    return {'status': 'success'}