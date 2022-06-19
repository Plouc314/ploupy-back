"""
Represents the arguments passed at each POST endpoint of the rest API
Each class matches a POST endpoint of the API
"""
from pydantic import BaseModel

from models.core import core

class CreateUser(core.User):
    pass


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
