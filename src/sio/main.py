import socketio
from pydantic import ValidationError

from src.core import PointModel, ResponseModel, logged
from src.game import (
    Game,
    GameConfig,
    ActionException,
    BuildFactoryResponse,
    GameStateModel,
    PlayerStateModel,
)

from .sio import sio
from .client import Client
from .state import State
from .job import JobManager
from .actions import ActionBuildFactoryModel, ActionExplodeProbesModel, ActionMoveProbesModel


app = socketio.ASGIApp(sio)

state = State()


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

    if sid in state.queue:
        state.queue.remove(sid)

    print(us.user.username, "disconnected")
    state.remove_user(sid)


@sio.event
async def join_queue(sid: str):
    """
    Make the user join the game queue
    Start a new game when the queue is full
    """
    state.queue.append(sid)
    if len(state.queue) < 2:
        return

    gid = state.get_gid()

    config = GameConfig(
        dim=PointModel(x=21, y=21),
        initial_money=100,
        factory_price=100,
        factory_max_probe=5,
        building_occupation_min=5,
        max_occupation=10,
        probe_speed=5,
        probe_price=10,
        income_rate=0.05,
        deprecate_rate=0.1,
    )
    job_manager = JobManager(gid)

    # create game
    users = [state.get_user(_id) for _id in state.queue]
    game = Game([user.user for user in users], job_manager, config)
    gs = state.add_game(gid, game, users)

    # create room
    for user in users:
        user.gid = gs.gid
        sio.enter_room(user.sid, room=gs.gid)

    # broadcast start game event
    await sio.emit("start_game", game.model.dict(), to=gs.gid)


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
