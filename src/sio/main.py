import socketio
from pydantic import ValidationError

from src.core import ActionException, logged

from src.models import core as _c
from src.models.sio import actions

from .sio import sio
from .client import client
from .manager.gamemanager import GameManager
from .manager.queuemanager import QueueManager
from .manager.usermanager import UserManager


app = socketio.ASGIApp(sio)

uman = UserManager()
qman = QueueManager()
gman = GameManager()


@sio.event
async def connect(sid: str, environ: dict):
    """
    Handle the connection, require a `http-uid` header
    """
    print(sid, "connected")
    uid = environ.get("HTTP_UID", None)

    if uid is None:
        return False

    response = await client.get_user_data(uid)

    if response is None:
        return False

    print(response.user.username, "connected")

    await uman.connect(sid, response.user)
    await qman.connect()
    await gman.connect()


@sio.event
async def disconnect(sid: str):
    us = uman.get_user(sid=sid)

    print(us.user.username, "disconnected")

    await gman.disconnect(us)
    await qman.disconnect(us)
    await uman.disconnect(us)


@sio.event
async def man_user_state(sid: str, data: dict) -> _c.Response:
    """
    Broadcast the current user manager state to requesting user
    """
    await sio.emit("man_user_state", uman.state.dict(), to=sid)

    return _c.Response().dict()


@sio.event
async def man_queue_state(sid: str, data: dict) -> _c.Response:
    """
    Broadcast the current manager queue state to requesting user
    """
    await sio.emit("man_queue_state", qman.state.dict(), to=sid)

    return _c.Response().dict()


@sio.event
async def man_game_state(sid: str, data: dict) -> _c.Response:
    """
    Broadcast the current game manager state to requesting game
    """
    await sio.emit("man_game_state", gman.state.dict(), to=sid)

    return _c.Response().dict()


@sio.event
async def create_queue(sid: str, data: dict) -> _c.Response:
    """
    Create a new queue
    inform connected users
    """
    us = uman.get_user(sid=sid)

    try:
        model = actions.CreateQueue(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    game_mode = await client.get_game_mode(id=model.gmid)

    if game_mode is None:
        return _c.Response(
            success=False, msg=f"Invalid game mode id '{model.gmid}'"
        ).dict()

    # create queue
    qs = qman.add_queue(game_mode)

    # add creator user
    qs.users.append(us)

    # notify all users
    await sio.emit("man_queue_state", qman.get_response([qs]).dict())

    return _c.Response().dict()


@sio.event
async def join_queue(sid: str, data: dict) -> _c.Response:
    """
    Make the user join the game queue
    Start a new game when the queue is full
    """
    us = uman.get_user(sid=sid)

    try:
        model = actions.JoinQueue(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    queue = qman.get_queue(model.qid)

    if queue is None:
        return _c.Response(
            success=False, msg=f"Queue not found (qid: {model.qid})"
        ).dict()

    if us in queue.users:
        return _c.Response(success=False, msg=f"Already in queue.").dict()

    # join the queue
    is_full = await qman.join_queue(queue, us)

    if not is_full:
        return _c.Response().dict()

    await gman.create_game(queue.users, queue.game_mode)

    return _c.Response().dict()


@sio.event
async def leave_queue(sid: str, data: dict) -> _c.Response:
    """
    Make the user leave the specified queue
    """
    us = uman.get_user(sid=sid)

    try:
        model = actions.LeaveQueue(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    queue = qman.get_queue(model.qid)

    if queue is None:
        return _c.Response(
            success=False, msg=f"Queue not found (qid: {model.qid})"
        ).dict()

    if not us in queue.users:
        return _c.Response(success=False, msg=f"Not in queue.").dict()

    qman.leave_queue(queue, us)

    # broadcast queue state
    await sio.emit("man_queue_state", qman.get_response([queue]).dict())

    return _c.Response().dict()


@sio.event
async def is_active_game(sid: str, data: dict) -> _c.Response:
    """
    Check if the user is currently in a game,
    if it is the case, broadcast a "start_game" event with the
    current game state to the user

    NOTE: if `us.gid` is not None -> return
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is not None:
        return _c.Response().dict()

    gs = gman.get_game(user=us.user)
    if gs is None:
        return _c.Response().dict()

    gman.link_user_to_game(gs, us)

    # broadcast start game event
    await sio.emit("start_game", gs.game.model.dict(), to=us.sid)

    return _c.Response().dict()


@sio.event
async def game_state(sid: str, data: dict) -> _c.Response:
    """
    Broadcast the current game state to requesting user
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").dict()

    await sio.emit("game_state", gs.game.model.dict(), to=us.sid)

    return _c.Response().dict()


@sio.event
async def action_resign_game(sid: str, data: dict) -> _c.Response:
    """
    Action that resign the game for a player
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").dict()

    try:
        model = actions.ResignGame(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        gs.game.action_resign_game(player)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).dict()

    return _c.Response().dict()


@sio.event
@logged("actions")
async def action_build_factory(sid: str, data: dict) -> _c.Response:
    """
    Action that build a new factory
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").dict()

    try:
        model = actions.BuildFactory(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_build_factory(player, model.coord)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).dict()

    await sio.emit("build_factory", response.dict(), to=gs.gid)

    return _c.Response().dict()


@sio.event
@logged("actions")
async def action_build_turret(sid: str, data: dict) -> _c.Response:
    """
    Action that build a new turret
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").dict()

    try:
        model = actions.BuildTurret(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_build_turret(player, model.coord)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).dict()

    await sio.emit("build_turret", response.dict(), to=gs.gid)

    return _c.Response().dict()


@sio.event
@logged("actions")
async def action_move_probes(sid: str, data: dict) -> _c.Response:
    """
    Action that change the position of some probes
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").dict()

    try:
        model = actions.MoveProbes(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_move_probes(player, model.ids, model.target)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).dict()

    await sio.emit("game_state", response.dict(), to=gs.gid)

    return _c.Response().dict()


@sio.event
@logged("actions")
async def action_explode_probes(sid: str, data: dict) -> _c.Response:
    """
    Action that explode some probes
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").dict()

    try:
        model = actions.ExplodeProbes(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_explode_probes(player, model.ids)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).dict()

    await sio.emit("game_state", response.dict(), to=gs.gid)

    return _c.Response().dict()


@sio.event
@logged("actions")
async def action_probes_attack(sid: str, data: dict) -> _c.Response:
    """
    Action that make some probes to attack an opponent
    """
    us = uman.get_user(sid=sid)

    gs = gman.get_game(gid=us.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").dict()

    try:
        model = actions.ProbesAttack(**data)
    except ValidationError as e:
        return _c.Response(success=False, msg="Invalid data").dict()

    player = gs.game.get_player(us.user.username)

    try:
        response = gs.game.action_probes_attack(player, model.ids)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).dict()

    await sio.emit("game_state", response.dict(), to=gs.gid)

    return _c.Response().dict()
