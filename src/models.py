from pydantic import BaseModel

class UserModel(BaseModel):
    uid: str
    username: str
    email: str