import socketio

from core import ALLOWED_ORIGINS

sio = socketio.AsyncServer(
    cors_allowed_origins=ALLOWED_ORIGINS,
    async_mode="asgi"
)