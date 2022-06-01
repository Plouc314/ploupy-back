import uuid
from pydantic import BaseModel

from src.core import UserModel
from src.game import Game, GameConfig

from .models import QueueStateResponse


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


class QueueState(BaseModel):
    qid: str
    """queue id"""
    active: bool
    users: list[UserState]
    config: GameConfig

    def get_response(self) -> QueueStateResponse:
        """
        Return the queue, casted as QueueStateResponse
        """
        return QueueStateResponse(
            qid=self.qid,
            active=self.active,
            n_player=self.config.n_player,
            users=[user.user.username for user in self.users],
        )


class State:
    def __init__(self):
        # keys: sid
        self.users: dict[str, UserState] = {}
        # keys: game id
        self.games: dict[str, GameState] = {}
        # keys: queue id
        self.queues: dict[str, QueueState] = {}

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

    def get_id(self) -> str:
        """
        Generate a random id
        """
        return uuid.uuid4().hex

    def get_game(self, gid: str) -> GameState | None:
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

    def get_queue(self, qid: str) -> QueueState | None:
        return self.queues.get(qid, None)

    def add_queue(self, config: GameConfig) -> QueueState:
        """
        Build an add a new QueueState object
        """
        qid = self.get_id()
        queue_state = QueueState(qid=qid, active=True, users=[], config=config)
        self.queues[qid] = queue_state
        return queue_state

    def remove_queue(self, qid: str) -> None:
        if qid in self.queues.keys():
            self.queues.pop(qid)
