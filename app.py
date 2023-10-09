import datetime as dt
from typing import Dict, List, Optional
from functools import wraps
import os

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2, OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.templating import Jinja2Templates

from jose import JWTError, jwt
from passlib.handlers.sha2_crypt import sha512_crypt as crypto

from sqlalchemy.orm import Session

from db import crud, models, schemas
from db.database import SessionLocal, engine

from dotenv import load_dotenv
load_dotenv()

models.Base.metadata.create_all(bind=engine)

def db_session_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        db_session = SessionLocal()
        try:
            result = func(*args, db_session=db_session, **kwargs)
            return result
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()
    return wrapper

class Settings:
    SECRET_KEY = os.environ['SECRET_KEY']
    ALGORITHM = os.environ['ALGORITHM']
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'])
    COOKIE_NAME = os.environ['COOKIE_NAME']


app = FastAPI()
templates = Jinja2Templates(directory="templates")
settings = Settings()

class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get(settings.COOKIE_NAME) 
        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="token")


def create_access_token(data: Dict) -> str:
    to_encode = data.copy()
    expire = dt.datetime.utcnow() + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

@db_session_decorator
def authenticate_user(email: str, plain_password: str, db_session: Session) -> models.User:
    user = crud.get_user_by_email(db_session, email)
    if not user:
        return False
    if not crypto.verify(plain_password, user.password):
        return False
    return user

@db_session_decorator
def decode_token(token: str, db_session: Session) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Could not validate credentials."
    )
    token = token.removeprefix("Bearer").strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
    except JWTError as e:
        print(e)
        raise credentials_exception
    user = crud.get_user_by_email(db_session, email)
    return user


def get_current_user_from_token(token: str = Depends(oauth2_scheme)) -> models.User:
    """
    Get the current user from the cookies in a request.

    Use this function when you want to lock down a route so that only 
    authenticated users can see access the route.
    """
    user = decode_token(token)
    return user


def get_current_user_from_cookie(request: Request) -> models.User:
    """
    Get the current user from the cookies in a request.
    
    Use this function from inside other routes to get the current user. Good
    for views that should work for both logged in, and not logged in users.
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    user = decode_token(token)
    return user


@app.post("token")
def login_for_access_token(
    response: Response, 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    user = authenticate_user(form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"email": user.email})
    response.set_cookie(
        key=settings.COOKIE_NAME, 
        value=f"Bearer {access_token}", 
        httponly=True
    )  
    return {settings.COOKIE_NAME: access_token, "token_type": "bearer"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    try:
        user = get_current_user_from_cookie(request)
    except:
        user = None
    context = {
        "user": user,
        "request": request,
    }
    return templates.TemplateResponse("index.html", context)



@app.get("/private", response_class=HTMLResponse)
def index(request: Request, user: models.User = Depends(get_current_user_from_token)):
    context = {
        "user": user,
        "request": request
    }
    return templates.TemplateResponse("private.html", context)

@app.get("/auth/login", response_class=HTMLResponse)
def login_get(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("login.html", context)


class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.msg: Optional[str] = None
        self.email: Optional[str] = None
        self.password: Optional[str] = None

    async def load_data(self):
        form = await self.request.form()
        self.email = form.get("email")
        self.password = form.get("password")

    def is_valid(self):
        if not self.email or not ("@" in self.email):
            self.errors.append("Email is required")
        if not self.password or not len(self.password) >= 4:
            self.errors.append("A valid password is required")
        if not self.errors:
            return True
        return False


@app.post("/auth/login", response_class=HTMLResponse)
async def login_post(request: Request):
    form = LoginForm(request)
    await form.load_data()
    if form.is_valid():
        try:
            response = RedirectResponse("/", status.HTTP_302_FOUND)
            login_for_access_token(response=response, form_data=form)
            form.msg = "Login Successful!"
            return response
        
        except HTTPException:
            form.msg = ""
            form.errors.append("Incorrect Email or Password")
            return templates.TemplateResponse("login.html", form.__dict__)
        
    return templates.TemplateResponse("login.html", form.__dict__)


@app.get("/auth/register", response_class=HTMLResponse)
def register_get(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("register.html", context)


class RegisterForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.errors: List = []
        self.user: Optional[schemas.User] = None

    async def load_data(self):
        form = await self.request.form()
        self.user = schemas.User(**form)

    async def is_valid(self):
        if len(self.user.password) < 4:
            self.errors.append("A password with length more than 3 required")
        if not self.errors:
            return True
        return False

@db_session_decorator
def create_user(user: schemas.User, db_session: Session):
    db_user = crud.get_user_by_email(db_session, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db_session, user=user)

@app.post("/auth/register", response_class=HTMLResponse)
async def register_post(request: Request):
    form = RegisterForm(request)
    await form.load_data()
    if await form.is_valid():
        try:
            form.user.password = crypto.hash(form.user.password)
            _ = create_user(form.user)
            response = RedirectResponse("/auth/login", status.HTTP_302_FOUND)
            form.msg = "Register Successful!"
            return response
        except HTTPException as e:
            form.msg = ""
            form.errors.append(e.detail)
            return templates.TemplateResponse("register.html", form.__dict__)
        
    return templates.TemplateResponse("register.html", form.__dict__)

@app.get("/auth/logout", response_class=HTMLResponse)
def login_get():
    response = RedirectResponse(url="/")
    response.delete_cookie(settings.COOKIE_NAME)
    return response