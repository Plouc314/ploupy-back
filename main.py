from src.api.api import app as rest_app
from src.sio.sio import app as sio_app

rest_app.mount("/ws", sio_app)