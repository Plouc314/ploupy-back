import uuid

from src.core import GameModeModel

from .models import QueueSioModel, QueueState, QueueStateResponse, UserSioModel
from .sio import sio


class QueueManager:
    def __init__(self):
        self._queues: dict[str, QueueSioModel] = {}

    def _get_queue_state(self, queue: QueueSioModel) -> QueueState:
        """
        Return sio queue casted to queue state
        """
        return QueueState(
            qid=queue.qid,
            active=queue.active,
            gmid=queue.game_mode.id,
            users=[user.user for user in queue.users],
        )

    def get_queues_response(self, queues: list[QueueSioModel]) -> QueueStateResponse:
        """
        Return a queue state response composed of the given queues
        """
        return QueueStateResponse(
            queues=[self._get_queue_state(queue) for queue in queues]
        )

    def get_queue(self, qid: str) -> QueueSioModel | None:
        """
        Get a queue by qid,
        return None if not found
        """
        return self._queues.get(qid, None)

    def add_queue(self, game_mode: GameModeModel) -> QueueSioModel:
        """
        Build an add a new QueueSioModel instance
        """
        qid = uuid.uuid4().hex
        queue_state = QueueSioModel(qid=qid, active=True, users=[], game_mode=game_mode)
        self._queues[qid] = queue_state
        return queue_state

    def get_queues_state(self) -> QueueStateResponse:
        """
        Return the state of all queues
        """
        return self.get_queues_response(self._queues.values())

    def leave_queue(self, queue: QueueSioModel, user: UserSioModel):
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

    async def leave_all_queues(self, user: UserSioModel):
        """
        Remove user from all queues where he's presents

        NOTE: Broadcast all queue changes to clients
        """
        to_update_qs = {}

        for queue in self._queues.values():
            if user in queue.users:
                to_update_qs[queue.qid] = queue

        queues = []

        for queue in to_update_qs.values():
            self.leave_queue(queue, user)
            queues.append(queue)

        await sio.emit("queue_state", self.get_queues_response(queues).dict())

    async def join_queue(self, queue: QueueSioModel, user: UserSioModel) -> bool:
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
            await sio.emit("queue_state", self.get_queues_response([queue]).dict())
            return False

        # queue is full
        self._queues.pop(queue.qid, None)
        queue.active = False

        updated_qs: list[QueueSioModel] = [queue]
        to_rem_qs: list[QueueSioModel] = []

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
        await sio.emit("queue_state", self.get_queues_response(updated_qs).dict())

        return True
