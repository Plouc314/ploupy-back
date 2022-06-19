"""
Represents the arguments passed at each endpoint of the rest API
Each class matches an endpoint of the API
"""
from pydantic import BaseModel

from src.models.core import core


class UserData(BaseModel):
    uid: str | None = None
    username: str | None = None


class CreateUser(core.User):
    pass


class GameMode(BaseModel):
    id: str | None = None
    all: bool | None = None


class GameResults(BaseModel):

    gmid: str
    """
    Game mode id of mode in which the game was played
    """
    ranking: list[str]
    """
    list of the `uid` of the users,
    from best (index: 0) to worst
    """


class UserStats(BaseModel):
    uid: str
