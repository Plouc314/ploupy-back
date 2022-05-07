from pydantic import BaseModel

from src.core import User


class Response(BaseModel):
    success: bool
    msg: str = ""


class UserResponse(Response):
    data: User

