import socketio
from pydantic import ValidationError

from src.core import PointModel, ResponseModel, logged
from src.game import (
    Game,
    GameConfig,
    ActionException,
)

from .sio import sio
from .client import Client
from .state import State
from .job import JobManager
from .models import (
    ActionBuildFactoryModel,
    ActionBuildTurretModel,
    ActionCreateQueueModel,
    ActionExplodeProbesModel,
    ActionJoinQueueModel,
    ActionLeaveQueueModel,
    ActionMoveProbesModel,
    ActionProbesAttackModel,
    QueueStateResponse,
)


app = socketio.ASGIApp(sio)

state = State()

DEFAULT_CONFIG = {
    "dim": {"x": 21, "y": 21},
    "initial_money": 100,
    "initial_n_probes": 3,
    "base_income": 6,
    "factory_price": 100,
    "factory_max_probe": 5,
    "factory_occupation_min": 5,
    "factory_build_probe_delay": 2,
    "max_occupation": 10,
    "probe_speed": 5,
    "probe_price": 10,
    "probe_maintenance_costs": 2,
    "turret_price": 70,
    "turret_fire_delay": 1,
    "turret_scope": 3,
    "income_rate": 0.05,
    "deprecate_rate": 0.1,
}

async def notify_queues_client(sid):
    await sio.sleep(1)
    # send all queue states
    for queue in state.queues.values():
        await sio.emit("queue_state", queue.get_response().dict(), to=sid)

@sio.event
async def connect(sid: str, environ: dict):
    """
    Handle the connection, require a `http-uid` header
    """
    print(sid, "connected")
    uid = environ.get("HTTP_UID", None)

    if uid is None:
        return False

    response = Client.get_user_data(uid)

    if not response.success:
        return False

    print(response.user.username, "connected")

    state.add_user(sid, response.user)

    sio.start_background_task(notify_queues_client, sid)

@sio.event
async def disconnect(sid: str):
    us = state.get_user(sid)

    for queue in state.queues.values():
        if us in queue.users:
            queue.users.remove(us)

    print(us.user.username, "disconnected")
    state.remove_user(sid)


@sio.event
async def create_queue(sid: str, data: dict) -> ResponseModel:
    """
    Create a new queue
    inform connected users
    """
    us = state.get_user(sid)

    try:
        model = ActionCreateQueueModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    config = GameConfig(**DEFAULT_CONFIG | model.dict())

    # create queue
    qs = state.add_queue(config)

    # add creator user
    qs.users.append(us)

    # notify all users
    await sio.emit("queue_state", qs.get_response().dict())

    return ResponseModel().dict()


@sio.event
async def join_queue(sid: str, data: dict) -> ResponseModel:
    """
    Make the user join the game queue
    Start a new game when the queue is full
    """
    us = state.get_user(sid)

    try:
        model = ActionJoinQueueModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    queue = state.get_queue(model.qid)

    if queue is None:
        return ResponseModel(
            success=False, msg=f"Queue not found (qid: {model.qid})"
        ).dict()

    if us in queue.users:
        return ResponseModel(success=False, msg=f"Already in queue.").dict()

    queue.users.append(us)

    # handle case: queue not full
    if len(queue.users) < queue.config.n_player:
        # broadcast queue state
        await sio.emit("queue_state", queue.get_response().dict())
        return ResponseModel().dict()

    # queue full -> remove queue
    state.remove_queue(queue.qid)
    queue.active = False
    
    # broadcast queue state
    await sio.emit("queue_state", queue.get_response().dict())

    # handle game creation
    gid = state.get_id()

    job_manager = JobManager(gid)

    # create game
    game = Game([user.user for user in queue.users], job_manager, queue.config)
    gs = state.add_game(gid, game, queue.users)

    # create room
    for user in queue.users:
        user.gid = gs.gid
        sio.enter_room(user.sid, room=gs.gid)

    # broadcast start game event
    await sio.emit("start_game", game.model.dict(), to=gs.gid)
    return ResponseModel().dict()

@sio.event
async def leave_queue(sid: str, data: dict) -> ResponseModel:
    '''
    Make the user leave the specified queue
    '''
    us = state.get_user(sid)

    try:
        model = ActionLeaveQueueModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    queue = state.get_queue(model.qid)

    if queue is None:
        return ResponseModel(
            success=False, msg=f"Queue not found (qid: {model.qid})"
        ).dict()

    if not us in queue.users:
        return ResponseModel(success=False, msg=f"Not in queue.").dict()

    # leave queue
    queue.users.remove(us)

    # check if still someone in queue
    if len(queue.users) == 0:
        state.remove_queue(queue.qid)

    # broadcast queue state
    await sio.emit("queue_state", queue.get_response().dict())
    return ResponseModel().dict()

@sio.event
@logged("actions")
async def action_build_factory(sid: str, data: dict) -> ResponseModel:
    """
    Action that build a new factory
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return

    try:
        model = ActionBuildFactoryModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_build_factory(player, model.coord)
    except ActionException as e:
        return ResponseModel(success=False, msg=str(e)).dict()

    await sio.emit("build_factory", response.dict(), to=gs.gid)

    return ResponseModel().dict()


@sio.event
@logged("actions")
async def action_build_turret(sid: str, data: dict) -> ResponseModel:
    """
    Action that build a new turret
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return

    try:
        model = ActionBuildTurretModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_build_turret(player, model.coord)
    except ActionException as e:
        return ResponseModel(success=False, msg=str(e)).dict()

    await sio.emit("build_turret", response.dict(), to=gs.gid)

    return ResponseModel().dict()


@sio.event
@logged("actions")
async def action_move_probes(sid: str, data: dict) -> ResponseModel:
    """
    Action that change the position of some probes
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return

    try:
        model = ActionMoveProbesModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_move_probes(player, model.ids, model.targets)
    except ActionException as e:
        return ResponseModel(success=False, msg=str(e)).dict()

    await sio.emit("game_state", response.dict(), to=gs.gid)

    return ResponseModel().dict()


@sio.event
@logged("actions")
async def action_explode_probes(sid: str, data: dict) -> ResponseModel:
    """
    Action that explode some probes
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return

    try:
        model = ActionExplodeProbesModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_explode_probes(player, model.ids)
    except ActionException as e:
        return ResponseModel(success=False, msg=str(e)).dict()

    await sio.emit("game_state", response.dict(), to=gs.gid)

    return ResponseModel().dict()


@sio.event
@logged("actions")
async def action_probes_attack(sid: str, data: dict) -> ResponseModel:
    """
    Action that make some probes to attack an opponent
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return

    try:
        model = ActionProbesAttackModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_probes_attack(player, model.ids)
    except ActionException as e:
        return ResponseModel(success=False, msg=str(e)).dict()

    await sio.emit("game_state", response.dict(), to=gs.gid)

    return ResponseModel().dict()
