import uuid
from pydantic import BaseModel

from src.core import UserModel
from src.game import Game, GameConfig

from .models import QueueState, QueueStateResponse
from .sio import sio
from .job import JobManager


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
    '''
    socket-io users that are currently connected
    NOTE: no assurance that all players users are there
    '''
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

    def get_game_by_user(self, user: UserModel) -> GameState | None:
        '''
        Search for a game with the user in it (not necessarily connected)
        '''
        for game in self.games.values():
            for player in game.game.players.values():
                if player.user.uid == user.uid:
                    return game
        return None

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

    def link_user_to_game(self, gs: GameState, user: UserState):
        '''
        - Make user enters the game room
        - Set user `gid` attribute
        - If not socket-io user in GameState, add it
        '''
        if not user in gs.users:
            gs.users.append(user)
        user.gid = gs.gid
        sio.enter_room(user.sid, room=gs.gid)

    async def create_game(self, users: list[UserState], config: GameConfig):
        """
        Create a new Game instance
        - Make all users enters the game room
        - Broadcast the start_game event
        """
        gid = self.get_id()

        job_manager = JobManager(gid)

        # create game
        game = Game(
            [user.user for user in users],
            job_manager,
            config,
            lambda g: self.end_game(gid),
        )
        gs = self.add_game(gid, game, users)

        # create room
        for user in users:
            self.link_user_to_game(gs, user)

        # broadcast start game event
        await sio.emit("start_game", game.model.dict(), to=gs.gid)

    def end_game(self, gid: str):
        """
        - Remove the game state from State
        - Make all users leave the game room
        - Reset game's users gid
        """
        gs = self.get_game(gid)

        if gs is None:
            return

        # remove game from games list
        self.remove_game(gid)

        # leave room
        for user in gs.users:
            user.gid = None
            sio.leave_room(user.sid, room=gid)

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

    async def leave_all_queues(self, user: UserState):
        """
        Remove user from all queues where he's presents

        NOTE: Broadcast all queue changes to clients
        """
        to_update_qs = {}

        for queue in self.queues.values():
            if user in queue.users:
                to_update_qs[queue.qid] = queue

        queue_states = []

        for queue in to_update_qs.values():
            self.leave_queue(queue, user)
            queue_states.append(queue.get_state())

        await sio.emit("queue_state", QueueStateResponse(queues=queue_states).dict())

    def disconnect_from_game(self, user: UserState):
        """
        Disconnect the (socket-io) user from the game
        NOTE: do NOT RESIGN the game for the user

        In case nobody is connected to the game anymore,
        end the game
        """
        game = self.get_game(user.gid)
        if game is None:
            return

        if user in game.users:
            game.users.remove(user)

        if len(game.users) == 0:
            game.game.end_game(notify_client=False)

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
