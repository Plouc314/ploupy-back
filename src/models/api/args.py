"""
Represents the arguments passed at each POST endpoint of the rest API
Each class matches a POST endpoint of the API
"""
from datetime import datetime
from pydantic import BaseModel

from src.models.core import core


class CreateUser(BaseModel):
    uid: str
    username: str
    email: str
    avatar: str
    joined_on: datetime


class UserOnline(BaseModel):
    jwt: str


class GameResults(BaseModel):

    siotk: str
    """
    Token of the socket-io client
    """

    gmid: str
    """
    Game mode id of mode in which the game was played
    """
    ranking: list[str]
    """
    list of the `uid` of the users,
    from best (index: 0) to worst
    """
