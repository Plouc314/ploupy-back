import uuid

from src.core import User
from src.game import Game

from .models import UserState, GameState


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

    def add_user(self, sid: str, user: User) -> UserState:
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

    def get_game(self, gid: str) -> GameState:
        return self.games[gid]

    def add_game(self, game: Game, users: list[UserState]) -> GameState:
        """
        Build and add a new GameState object from the given game  
        Generate a random id for the game  
        Return the GameState
        """
        gid = uuid.uuid4().hex
        game_state = GameState(gid=gid, game=game, users=users)
        self.games[gid] = game_state
        return game_state

    def remove_game(self, gid: str) -> None:
        if gid in self.games.keys():
            self.games.pop(gid)
