"""
Represents the arguments passed at each POST endpoint of the rest API
Each class matches a POST endpoint of the API
"""
from datetime import datetime
from pydantic import BaseModel

from src.models.core import core


class CreateUser(core.User):
    last_online: datetime | None = None


class CreateBot(BaseModel):
    creator_uid: str
    """
    uid of the bot creator
    """
    username: str
    """
    Username of the bot
    """


class UserOnline(BaseModel):
    siotk: str
    """
    Token of the socket-io server
    """
    uid: str


class GameResults(BaseModel):

    siotk: str
    """
    Token of the socket-io server
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
