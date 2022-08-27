import logging
import socketio

from src.core import ActionException, setup_logger

from src.models import core as _c, sio as _s
from src.models.sio import actions, responses

from .sio import sio
from .client import client
from .manager.gamemanager import GameManager
from .manager.queuemanager import QueueManager
from .manager.usermanager import UserManager
import src.sio.decorators as deco

setup_logger(logging.INFO)

logger = logging.getLogger("ploupy")

app = socketio.ASGIApp(sio)

uman = UserManager()
qman = QueueManager()
gman = GameManager()


@sio.event
async def connect(sid: str, environ: dict):
    """
    Handle the connection

    Require a `http-firebase-jwt` header for web client auth, else fall back to visitor
    """
    if uman.get_user(sid=sid) is not None:
        return False

    firebase_jwt = environ.get("HTTP_FIREBASE_JWT", None)
    bot_jwt = environ.get("HTTP_BOT_JWT", None)

    pers = await uman.connect(sid, firebase_jwt=firebase_jwt, bot_jwt=bot_jwt)

    if isinstance(pers, _s.User):
        logger.info(f"[{pers.sid[:3]}] {pers.user.username} connected")
    else:
        logger.info(f"[{pers.sid[:3]}] visitor connected")

    await qman.connect()
    await gman.connect()


@sio.event
async def disconnect(sid: str):

    us = uman.get_user(sid=sid)
    vis = uman.get_visitor(sid)

    if us is not None:
        logger.info(f"[{us.sid[:3]}] {us.user.username} disconnected")

        # update last online time
        await client.post_user_online(us)
    else:
        logger.info(f"[{vis.sid[:3]}] visitor disconnected")

    pers = us if vis is None else vis

    await gman.disconnect(pers)
    await qman.disconnect(pers)
    await uman.disconnect(pers)


@sio.event
async def man_user_state(sid: str, data: dict) -> _c.Response:
    """
    Broadcast the current user manager state to requesting user
    """
    await sio.emit("man_user_state", uman.state.json(), to=sid)

    return _c.Response().json()


@sio.event
async def man_queue_state(sid: str, data: dict) -> _c.Response:
    """
    Broadcast the current manager queue state to requesting user
    """
    await sio.emit("man_queue_state", qman.state.json(), to=sid)

    return _c.Response().json()


@sio.event
async def man_game_state(sid: str, data: dict) -> _c.Response:
    """
    Broadcast the current game manager state to requesting game
    """
    await sio.emit("man_game_state", gman.state.json(), to=sid)

    return _c.Response().json()


@sio.on("create_queue")
@deco.with_user(uman)
@deco.with_model(actions.CreateQueue)
async def create_queue(us: _s.User, model: actions.CreateQueue) -> _c.Response:
    """
    Create a new queue
    inform connected users
    """
    game_mode = await client.get_game_mode(id=model.gmid)

    if game_mode is None:
        return _c.Response(
            success=False, msg=f"Invalid game mode id '{model.gmid}'"
        ).json()

    # create queue
    qs = qman.add_queue(
        game_mode=game_mode,
        game_metadata=model.metadata,
    )

    # add creator user
    qs.users.append(us)

    # notify all users
    await sio.emit("man_queue_state", qman.get_response([qs]).json())

    return _c.Response().json()


@sio.on("join_queue")
@deco.with_user(uman)
@deco.with_model(actions.JoinQueue)
async def join_queue(us: _s.User, model: actions.JoinQueue) -> _c.Response:
    """
    Make the user join the game queue
    Start a new game when the queue is full
    """
    queue = qman.get_queue(model.qid)

    if queue is None:
        return _c.Response(
            success=False, msg=f"Queue not found (qid: {model.qid})"
        ).json()

    if us in queue.users:
        return _c.Response(success=False, msg=f"Already in queue.").json()

    # join the queue
    is_full = await qman.join_queue(queue, us)

    if not is_full:
        return _c.Response().json()

    await gman.create_game(queue.users, queue.game_mode, queue.game_metadata)

    return _c.Response().json()


@sio.on("leave_queue")
@deco.with_user(uman)
@deco.with_model(actions.LeaveQueue)
async def leave_queue(us: _s.User, model: actions.LeaveQueue) -> _c.Response:
    """
    Make the user leave the specified queue
    """
    queue = qman.get_queue(model.qid)

    if queue is None:
        return _c.Response(
            success=False, msg=f"Queue not found (qid: {model.qid})"
        ).json()

    if not us in queue.users:
        return _c.Response(success=False, msg=f"Not in queue.").json()

    qman.leave_queue(queue, us)

    # broadcast queue state
    await sio.emit("man_queue_state", qman.get_response([queue]).json())

    return _c.Response().json()


@sio.on("send_queue_invitation")
@deco.with_user(uman)
@deco.with_model(actions.SendQueueInvitation)
async def send_queue_invitation(
    us: _s.User, model: actions.SendQueueInvitation
) -> _c.Response:
    """
    Send an invitation to a user to join a queue
    """
    queue = qman.get_queue(model.qid)

    if queue is None:
        return _c.Response(
            success=False, msg=f"Queue not found (qid: {model.qid})"
        ).json()

    target_user = uman.get_user(uid=model.uid)
    if target_user is None:
        return _c.Response(success=False, msg=f"Invited user not connected.").json()

    await sio.emit(
        "queue_invitation",
        responses.QueueInvitation(qid=queue.qid).json(),
        to=target_user.sid,
    )

    return _c.Response().json()


@sio.on("disconnect_bot")
@deco.with_user(uman)
@deco.with_model(actions.DisconnectBot)
async def send_queue_invitation(
    us: _s.User, model: actions.DisconnectBot
) -> _c.Response:
    """
    Disconnect a bot of the user
    """
    if model.bot_uid not in us.user.bots:
        return _c.Response(success=False, msg=f"Bot uid is invalid.").json()

    bot = uman.get_user(uid=model.bot_uid)
    if bot is None:
        return _c.Response(success=False, msg=f"Bot is offline.").json()

    await sio.disconnect(bot.sid)

    return _c.Response().json()


@sio.on("is_active_game")
@deco.with_user(uman)
async def is_active_game(us: _s.User, data: dict) -> _c.Response:
    """
    Check if the user is currently in some game(s),
    if it is the case, broadcast a "start_game" event with the
    current game state to the user for each game
    """
    for gs in gman.get_user_games(us.user):

        if gs.gid in us.gids:
            continue

        gman.link_user_to_game(gs, us)

        # broadcast start game event
        await sio.emit("start_game", responses.StartGame(gid=gs.gid).json(), to=us.sid)

    return _c.Response().json()


@sio.on("game_state")
@deco.with_model(actions.GameState)
async def game_state(sid: str, model: actions.GameState) -> _c.Response:
    """
    - Link user to the game
    - Broadcast the current game state to requesting user
    """
    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    us = uman.get_user(sid=sid)
    if us is not None:
        gman.link_user_to_game(gs, us)

    vis = uman.get_visitor(sid)
    if vis is not None:
        gman.link_visitor_to_game(gs, vis)

    await sio.emit("game_state", gs.game.model.json(), to=sid)

    return _c.Response().json()


@sio.on("action_resign_game")
@deco.with_user(uman)
@deco.with_model(actions.ResignGame)
async def action_resign_game(us: _s.User, model: actions.ResignGame) -> _c.Response:
    """
    Action that resign the game for a player
    """
    if not model.gid in us.gids:
        return _c.Response(success=False, msg="User not in game.").json()

    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    try:
        gs.game.action_resign_game(us.user.uid)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).json()

    return _c.Response().json()


@sio.on("action_build_factory")
@deco.with_user(uman)
@deco.with_model(actions.BuildFactory)
async def action_build_factory(us: _s.User, model: actions.BuildFactory) -> _c.Response:
    """
    Action that build a new factory
    """
    if not model.gid in us.gids:
        return _c.Response(success=False, msg="User not in game.").json()

    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    try:
        gs.game.action_build_factory(us.user.uid, model.coord)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).json()

    return _c.Response().json()


@sio.on("action_build_turret")
@deco.with_user(uman)
@deco.with_model(actions.BuildTurret)
async def action_build_turret(us: _s.User, model: actions.BuildTurret) -> _c.Response:
    """
    Action that build a new turret
    """
    if not model.gid in us.gids:
        return _c.Response(success=False, msg="User not in game.").json()

    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    try:
        gs.game.action_build_turret(us.user.uid, model.coord)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).json()

    return _c.Response().json()


@sio.on("action_move_probes")
@deco.with_user(uman)
@deco.with_model(actions.MoveProbes)
async def action_move_probes(us: _s.User, model: actions.MoveProbes) -> _c.Response:
    """
    Action that change the position of some probes
    """
    if not model.gid in us.gids:
        return _c.Response(success=False, msg="User not in game.").json()

    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    try:
        gs.game.action_move_probes(us.user.uid, model.ids, model.target)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).json()

    return _c.Response().json()


@sio.on("action_explode_probes")
@deco.with_user(uman)
@deco.with_model(actions.ExplodeProbes)
async def action_explode_probes(
    us: _s.User, model: actions.ExplodeProbes
) -> _c.Response:
    """
    Action that explode some probes
    """
    if not model.gid in us.gids:
        return _c.Response(success=False, msg="User not in game.").json()

    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    try:
        gs.game.action_explode_probes(us.user.uid, model.ids)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).json()

    return _c.Response().json()


@sio.on("action_probes_attack")
@deco.with_user(uman)
@deco.with_model(actions.ProbesAttack)
async def action_probes_attack(us: _s.User, model: actions.ProbesAttack) -> _c.Response:
    """
    Action that make some probes to attack an opponent
    """
    if not model.gid in us.gids:
        return _c.Response(success=False, msg="User not in game.").json()

    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    try:
        gs.game.action_probes_attack(us.user.uid, model.ids)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).json()

    return _c.Response().json()


@sio.on("action_acquire_tech")
@deco.with_user(uman)
@deco.with_model(actions.AcquireTech)
async def action_acquire_tech(us: _s.User, model: actions.AcquireTech) -> _c.Response:
    """
    Action that acquire the given technology
    """
    if not model.gid in us.gids:
        return _c.Response(success=False, msg="User not in game.").json()

    gs = gman.get_game(gid=model.gid)
    if gs is None:
        return _c.Response(success=False, msg="Game not found").json()

    try:
        gs.game.action_acquire_tech(us.user.uid, model.tech)
    except ActionException as e:
        return _c.Response(success=False, msg=str(e)).json()

    return _c.Response().json()
