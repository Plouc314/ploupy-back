import socketio

from src.core import User
from src.game import Game, GameConfig, Point2D, PlayerStateClient

from .client import Client
from .state import State

sio = socketio.AsyncServer(
    cors_allowed_origins=["http://localhost:3000"],
    async_mode="asgi"
)
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

    print(response.data.username, "connected")

    state.add_user(sid, response.data)


@sio.event
async def disconnect(sid: str):
    user = state.get_user(sid)

    if sid in state.queue:
        state.queue.remove(sid)

    print(user.user.username, "disconnected")
    state.remove_user(sid)


@sio.event
async def join_queue(sid: str):
    state.queue.append(sid)
    if len(state.queue) < 2:
        return

    # create game
    users = [state.get_user(_id) for _id in state.queue]
    game = Game([user.user for user in users], GameConfig(dim=Point2D(x=20, y=20)))
    game_state = state.add_game(game, users)

    # create room
    for user in users:
        user.gid = game_state.gid
        sio.enter_room(user.sid, room=game_state.gid)

    # broadcast start game event
    await sio.emit("start_game", game.get_game_state().dict(), to=game_state.gid)


@sio.event
async def player_state(sid: str, data: PlayerStateClient):
    user = state.get_user(sid)
    if user.gid is None:
        return

    game = state.get_game(user.gid)

    player_state = game.game.update_player_state(
        user.user.username,
        PlayerStateClient(**data)
    )

    await sio.emit("player_state", player_state.dict(), to=game.gid)

