import socketio
from src.core import User

from src.game import (
    Game,
    GameConfig,
    Point2D,
    PlayerStateClient,
    PlayerStateServer
)

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
app = socketio.ASGIApp(sio)

users = []
game: Game = None
queue = []


@sio.event
async def connect(sid, environ):
    
    uid = environ["HTTP_UID"]
    with sio.session() as session:
        pass
    users.append(sid)

@sio.event
async def disconnect(sid):
    print(sid, "disconnected")
    users.remove(sid)

@sio.event
async def join_game(sid, username: str):
    global game
    queue.append(username)
    if len(queue) == 2:
        users = [User(uid="",username=u, email="") for u in queue]
        game = Game(users, GameConfig(dim=Point2D(x=20, y=20)))

@sio.event
async def player_state(sid, data: PlayerStateClient):
    if game is None:
        return
    state = game.on_player_update(data)
    await sio.emit("player_state", state, skip_sid=sid)
