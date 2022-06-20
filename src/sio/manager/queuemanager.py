import uuid

from models import core as _c, sio as _s

from .manager import Manager
from ..sio import sio


class QueueManager(Manager):
    """
    Manager of game queues
    """

    def __init__(self):
        self._queues: dict[str, _s.Queue] = {}

    def _get_queue_state(self, queue: _s.Queue) -> _s.QueueState:
        """
        Return sio.Queue casted to QueueState
        """
        return _s.QueueState(
            qid=queue.qid,
            active=queue.active,
            gmid=queue.game_mode.id,
            users=[user.user for user in queue.users],
        )

    def get_response(self, queues: list[_s.Queue]) -> _s.responses.QueueManagerState:
        """
        Return a queue state response composed of the given queues
        """
        return _s.responses.QueueManagerState(
            queues=[self._get_queue_state(queue) for queue in queues]
        )

    def get_queue(self, qid: str) -> _s.Queue | None:
        """
        Get a queue by qid,
        return None if not found
        """
        return self._queues.get(qid, None)

    def add_queue(self, game_mode: _c.GameMode) -> _s.Queue:
        """
        Build an add a new _s.Queue instance
        """
        qid = uuid.uuid4().hex
        queue_state = _s.Queue(qid=qid, active=True, users=[], game_mode=game_mode)
        self._queues[qid] = queue_state
        return queue_state

    def leave_queue(self, queue: _s.Queue, user: _s.User):
        """
        Remove the user from the queue,
        if no one left in queue, remove it from state queues

        NOTE: do not broadcast queue state
        """
        # leave queue
        if user in queue.users:
            queue.users.remove(user)

        # check if still someone in queue
        if len(queue.users) == 0:
            self._queues.pop(queue.qid, None)

    async def connect(self):
        """
        Pass
        """

    async def disconnect(self, user: _s.User):
        """
        - Remove user from all queues where he's presents
        - Broadcast all queue changes to clients
        """
        to_update_qs = {}

        for queue in self._queues.values():
            if user in queue.users:
                to_update_qs[queue.qid] = queue

        queues = []

        for queue in to_update_qs.values():
            self.leave_queue(queue, user)
            queues.append(queue)

        await sio.emit("man_queue_state", self.get_response(queues).dict())

    async def join_queue(self, queue: _s.Queue, user: _s.User) -> bool:
        """
        Add the user to the queue.
        In case the queue is full:
        - Make all the users in the queue leave
            all other queues they may be in.
        - Remove the queue

        NOTE: Broadcast all queue changes to clients

        Return if the queue is full
        """
        # add user
        queue.users.append(user)

        if len(queue.users) < queue.game_mode.config.n_player:
            await sio.emit("man_queue_state", self.get_response([queue]).dict())
            return False

        # queue is full
        self._queues.pop(queue.qid, None)
        queue.active = False

        updated_qs: list[_s.Queue] = [queue]
        to_rem_qs: list[_s.Queue] = []

        # leave other queues
        for q in self._queues.values():
            if q is queue:
                continue

            for user in queue.users:
                if user in q.users:
                    q.users.remove(user)
                    if not q in updated_qs:
                        updated_qs.append(q)

                    if len(q.users) == 0 and not q in to_rem_qs:
                        to_rem_qs.append(q)

        for q in to_rem_qs:
            self._queues.pop(q.qid, None)

        # broadcast updated queues
        await sio.emit("man_queue_state", self.get_response(updated_qs).dict())

        return True

    @property
    def state(self) -> _s.responses.QueueManagerState:
        return self.get_response(self._queues.values())
