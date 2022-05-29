import uuid
from pydantic import BaseModel

from src.core import UserModel
from src.game import Game


class UserState(BaseModel):
    sid: str
    """socketio id for user session"""
    user: UserModel
    gid: str | None = None
    """game id"""


class GameState(BaseModel):
    gid: str
    """game id"""
    users: list[UserState]
    game: Game

    class Config:
        arbitrary_types_allowed = True


class State:
    def __init__(self):
        self.users: dict[str, UserState] = {}
        """Keys: sid"""
        self.games: dict[str, GameState] = {}
        """Keys: game id"""
        self.queue: list[str] = []
        """Main queue"""

    def get_user(self, sid: str) -> UserState | None:
        return self.users.get(sid, None)

    def add_user(self, sid: str, user: UserModel) -> UserState:
        """
        Build and add a new UserState object from the given user
        Return the GameState
        """
        user_state = UserState(sid=sid, user=user)
        self.users[sid] = user_state
        return user_state

    def remove_user(self, sid: str) -> None:
        if sid in self.users.keys():
            self.users.pop(sid)

    def get_gid(self) -> str:
        '''
        Generate a random id for the game
        '''
        return uuid.uuid4().hex 

    def get_game(self, gid: str) -> GameState:
        return self.games.get(gid, None)

    def add_game(self, gid: str, game: Game, users: list[UserState]) -> GameState:
        """
        Build and add a new GameState object from the given game
        Return the GameState
        """
        game_state = GameState(gid=gid, game=game, users=users)
        self.games[gid] = game_state
        return game_state

    def remove_game(self, gid: str) -> None:
        if gid in self.games.keys():
            self.games.pop(gid)
