from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.firebase import Firebase
from src.models import UserModel

# app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Firebase.auth()

@app.get("/ping")
def ping():
    return "Hello world!"

@app.post("/api/create-user")
def create_user(data: UserModel):
    print(data)
    return data