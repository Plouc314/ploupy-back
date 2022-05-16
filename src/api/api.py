from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core import ResponseModel, UserModel, ALLOWED_ORIGINS

from .firebase import Firebase
from .response import UserResponse

# app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

firebase = Firebase()


@app.get("/ping")
def ping():
    return "Hello world!"


@app.get("/api/user-data")
def user_data(uid: str | None=None, username: str | None=None) -> ResponseModel:
    """
    Return the user data corresponding to the given uid
    """
    user = firebase.get_user(uid=uid, username=username)

    if user is None:
        return ResponseModel(success=False, msg="User not found.")

    return UserResponse(
        success=True,
        user=user,
    )


@app.post("/api/create-user")
def create_user(data: UserModel) -> ResponseModel:
    '''
    Create the user if possible and return if it was succesful
    '''
    user = firebase.get_user(uid=data.uid)
    
    if user is not None:
        return ResponseModel(success=False, msg=f"User already exists")
    
    firebase.create_user(data)

    return ResponseModel(success=True)
    
