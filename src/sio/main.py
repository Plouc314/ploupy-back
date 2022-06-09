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
    ActionResignGameModel,
    QueueStateResponse,
)


app = socketio.ASGIApp(sio)

state = State()

DEFAULT_CONFIG = GameConfig(
    dim=PointModel(x=21, y=21),
    n_player=2,
    initial_money=100,
    initial_n_probes=3,
    base_income=6,
    building_occupation_min=5,
    factory_price=100,
    factory_max_probe=5,
    factory_build_probe_delay=2,
    max_occupation=10,
    probe_speed=5,
    probe_price=10,
    probe_claim_delay=0.5,
    probe_maintenance_costs=2,
    turret_price=70,
    turret_fire_delay=1,
    turret_scope=3,
    turret_maintenance_costs=3,
    income_rate=0.05,
    deprecate_rate=0.1,
)


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


@sio.event
async def disconnect(sid: str):
    us = state.get_user(sid)

    print(us.user.username, "disconnected")

    await state.leave_all_queues(us)

    # disconnect from potential active game
    state.disconnect_from_game(us)

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

    config = GameConfig(**DEFAULT_CONFIG.dict() | model.dict())

    # create queue
    qs = state.add_queue(config)

    # add creator user
    qs.users.append(us)

    # notify all users
    await sio.emit("queue_state", qs.get_response().dict())

    return ResponseModel().dict()


@sio.event
async def queue_state(sid: str, data: dict) -> ResponseModel:
    """
    Broadcast the current queue state to requesting user
    """
    await sio.emit("queue_state", state.get_queues_state().dict(), to=sid)

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

    # join the queue
    is_full = await state.join_queue(queue, us)

    if not is_full:
        return ResponseModel().dict()

    await state.create_game(queue.users, queue.config)

    return ResponseModel().dict()


@sio.event
async def leave_queue(sid: str, data: dict) -> ResponseModel:
    """
    Make the user leave the specified queue
    """
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

    state.leave_queue(queue, us)

    # broadcast queue state
    await sio.emit("queue_state", queue.get_response().dict())

    return ResponseModel().dict()


@sio.event
async def is_active_game(sid: str, data: dict) -> ResponseModel:
    """
    Check if the user is currently in a game,
    if it is the case, broadcast a "start_game" event with the
    current game state to the user

    NOTE: if `us.gid` is not None -> return
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is not None:
        return ResponseModel().dict()

    gs = state.get_game_by_user(us.user)
    if gs is None:
        return ResponseModel().dict()

    state.link_user_to_game(gs, us)

    # broadcast start game event
    await sio.emit("start_game", gs.game.model.dict(), to=us.sid)

    return ResponseModel().dict()


@sio.event
async def game_state(sid: str, data: dict) -> ResponseModel:
    """
    Broadcast the current game state to requesting user
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return ResponseModel(success=False, msg="Game not found").dict()

    await sio.emit("game_state", gs.game.model.dict(), to=us.sid)

    return ResponseModel().dict()


@sio.event
async def action_resign_game(sid: str, data: dict) -> ResponseModel:
    """
    Action that resign the game for a player
    """
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return ResponseModel(success=False, msg="Game not found").dict()

    try:
        model = ActionResignGameModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        gs.game.action_resign_game(player)
    except ActionException as e:
        return ResponseModel(success=False, msg=str(e)).dict()

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
        return ResponseModel(success=False, msg="Game not found").dict()

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
        return ResponseModel(success=False, msg="Game not found").dict()

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
        return ResponseModel(success=False, msg="Game not found").dict()

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
        return ResponseModel(success=False, msg="Game not found").dict()

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
        return ResponseModel(success=False, msg="Game not found").dict()

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
