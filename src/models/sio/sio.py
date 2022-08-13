from pydantic import BaseModel

from src.models import core as _c
from src.sio import Game


class Person(BaseModel):
    """
    Represents someone connected to the sio server,
    that may be authentificated or not.
    """

    sid: str
    """socketio id for user session"""
    gid: str | None = None
    """game id of currently spectated/played game"""


class Visitor(Person):
    """
    Represents a Visitor in sio server

    The visitor is not authentificated and thus doesn't match
    a core.User.
    """


class User(Person):
    """
    Represents a User in sio server

    Which is effectively a wrapper for the core.User instance,
    plus metadata used by sio
    """

    user: _c.User


class UserState(BaseModel):
    """
    Represents a user's current state
    """

    connected: bool
    user: _c.User


class Queue(BaseModel):
    """
    Represents a queue (purely sio)
    """

    qid: str
    """queue id"""
    active: bool
    users: list[User]
    game_mode: _c.GameMode


class QueueState(BaseModel):
    """
    Represents a queue's current state
    """

    qid: str
    """id of the queue"""
    active: bool
    """if the queue is still active"""
    gmid: str
    """game mode id"""
    users: list[_c.User]
    """List of the users in the queue"""


class Game(BaseModel):
    """
    Represents a game in sio server

    Which is effectively a wrapper for the Game instance,
    plus metadata used by sio
    """

    gid: str
    """game id"""
    mode: _c.GameMode
    """
    Game mode of the game
    """
    players: list[User]
    """
    players (sio users) that are currently connected
    NOTE: no assurance that all players in game are currently connected
    """
    spectators: list[Person]
    """
    spectators (sio users/visitors) that are currently connected
    """
    game: Game
    """
    Actual game instance
    """

    class Config:
        arbitrary_types_allowed = True


class GameState(BaseModel):
    """
    Represents a game's current state
    """

    gid: str
    """game id"""
    active: bool
    """if the game is still active"""
    gmid: str
    """game mode id"""
    users: list[_c.User]
    """List of the users in the game"""
