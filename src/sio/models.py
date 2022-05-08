from pydantic import BaseModel

from src.core import User
from src.game import Game

class UserState(BaseModel):
    sid: str
    '''socketio id for user session'''
    user: User
    gid: str | None = None
    '''game id'''


class GameState(BaseModel):
    gid: str
    '''game id'''
    users: list[UserState]
    game: Game

    class Config:
        arbitrary_types_allowed = True