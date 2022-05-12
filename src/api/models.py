from pydantic import BaseModel
from typing import Any

from src.core import User


class Response(BaseModel):
    success: bool
    msg: str = ""
    data: Any = None


class UserResponse(Response):
    data: User = None

