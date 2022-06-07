import uuid
from pydantic import BaseModel

from src.core import UserModel
from src.game import Game, GameConfig

from .models import QueueState, QueueStateResponse
from .sio import sio


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


class Queue(BaseModel):
    qid: str
    """queue id"""
    active: bool
    users: list[UserState]
    config: GameConfig

    def get_state(self) -> QueueState:
        """
        Return the queue, casted as QueueState
        """
        return QueueState(
            qid=self.qid,
            active=self.active,
            n_player=self.config.n_player,
            users=[user.user for user in self.users],
        )

    def get_response(self) -> QueueStateResponse:
        """
        Return a queue state response composed of only this queue
        """
        return QueueStateResponse(queues=[self.get_state()])


class State:
    def __init__(self):
        # keys: sid
        self.users: dict[str, UserState] = {}
        # keys: game id
        self.games: dict[str, GameState] = {}
        # keys: queue id
        self.queues: dict[str, Queue] = {}

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

    def get_queue(self, qid: str) -> Queue | None:
        return self.queues.get(qid, None)

    def add_queue(self, config: GameConfig) -> Queue:
        """
        Build an add a new QueueState object
        """
        qid = self.get_id()
        queue_state = Queue(qid=qid, active=True, users=[], config=config)
        self.queues[qid] = queue_state
        return queue_state

    def remove_queue(self, qid: str) -> None:
        if qid in self.queues.keys():
            self.queues.pop(qid)

    def get_queues_state(self) -> QueueStateResponse:
        """
        Return the state of all queues
        """
        return QueueStateResponse(
            queues=[queue.get_state() for queue in self.queues.values()]
        )

    def leave_queue(self, queue: Queue, user: UserState):
        """
        Remove the user from the queue,
        if no one left in queue, remove it from state queues
        """
        # leave queue
        if user in queue.users:
            queue.users.remove(user)

        # check if still someone in queue
        if len(queue.users) == 0:
            self.remove_queue(queue.qid)

    async def join_queue(self, queue: Queue, user: UserState) -> bool:
        """
        Add the user to the queue.
        In case the queue is full:
        - Make all the users in the queue leave
            all other queues they may be in.
        - Remove the queue (call `self.remove_queue`)

        NOTE: Broadcast all queue changes to clients

        Return if the queue is full
        """
        # add user
        queue.users.append(user)

        if len(queue.users) < queue.config.n_player:
            await sio.emit(
                "queue_state", QueueStateResponse(queues=[queue.get_state()]).dict()
            )
            return False

        # queue is full
        self.remove_queue(queue.qid)
        queue.active = False

        updated_qs: list[QueueState] = [queue.get_state()]
        to_rem_qs: list[Queue] = []

        # leave other queues
        for q in self.queues.values():
            if q is queue:
                continue

            for user in queue.users:
                if user in q.users:
                    q.users.remove(user)
                    if not q in updated_qs:
                        updated_qs.append(q.get_state())

                    if len(q.users) == 0 and not q in to_rem_qs:
                        to_rem_qs.append(q)

        for q in to_rem_qs:
            self.remove_queue(q.qid)

        # broadcast updated queues
        await sio.emit("queue_state", QueueStateResponse(queues=updated_qs).dict())

        return True
