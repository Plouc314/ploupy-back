import socketio
from pydantic import ValidationError

from src.core import PointModel, ResponseModel, ALLOWED_ORIGINS
from src.game import Game, GameConfig, ActionException

from .sio import sio
from .client import Client
from .state import State
from .job import JobManager
from .response import ActionBuildResponse
from .actions import ActionBuildModel

app = socketio.ASGIApp(sio)

state = State()

def task(msg: str):
    pass

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
    state.queue.append(sid)
    if len(state.queue) < 2:
        return

    gid = state.get_gid()

    config = GameConfig(dim=PointModel(x=10, y=10), initial_money=10, factory_price=3, building_occupation_min=0)
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
async def action_build(sid: str, data: dict) -> ResponseModel:
    us = state.get_user(sid)

    gs = state.get_game(us.gid)
    if gs is None:
        return

    try:
        action_mod = ActionBuildModel(**data)
    except ValidationError as e:
        return ResponseModel(success=False, msg="Invalid data").dict()
    
    player = gs.game.get_player(us.user.username)

    try:
        model = gs.game.build_factory(player, action_mod.coord)
    except ActionException as e:
        return ResponseModel(success=False, msg=str(e)).dict()
    
    response = ActionBuildResponse(username=us.user.username, factory=model)

    await sio.emit("action_build", response.dict(), to=gs.gid)

    return ResponseModel().dict()

