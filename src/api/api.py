from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from src.core import User

from .models import UserResponse
from .firebase import Firebase
from .users import get_user

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

@app.get("/api/user-data")
def user_data(uid: str) -> UserResponse:
    '''
    Return the user data corresponding to the given uid
    '''
    user = get_user(uid=uid)

    if user is None:
        return UserResponse(
            success=False,
            msg="User not found."
        )
    
    return UserResponse(
        success=True,
        data=user,
    )


@app.post("/api/create-user")
def create_user(data: User):
    print(data)
    return data