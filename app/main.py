from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, external, info

app = FastAPI()

origins = [
    "https://aorta-detection.aspresearch.space",
    "http://localhost:5173",
    "http://92.100.20.67:5173",
    "http://10.102.105.20:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, tags=["Auth"], prefix="/api/auth")
app.include_router(info.router, tags=["Info"], prefix="/api/info")
app.include_router(external.router, tags=["External"], prefix="/api/external")


@app.get("/api/healthchecker")
def root():
    return {"message": "Hello World"}
