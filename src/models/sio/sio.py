from pydantic import BaseModel

from src.models.core import core

from src.game.game import Game


class User(BaseModel):
    """
    Represents a User in sio server

    Which is effectively a wrapper for the core.User instance,
    plus metadata used by sio
    """

    sid: str
    """socketio id for user session"""
    user: core.User
    gid: str | None = None
    """game id"""


class Queue(BaseModel):
    """
    Represents a queue (purely sio)
    """

    qid: str
    """queue id"""
    active: bool
    users: list[User]
    game_mode: core.GameMode


class Game(BaseModel):
    """
    Represents a game in sio server

    Which is effectively a wrapper for the Game instance,
    plus metadata used by sio
    """

    gid: str
    """game id"""
    mode: core.GameMode
    """
    Game mode of the game
    """
    users: list[User]
    """
    socket-io users that are currently connected
    NOTE: no assurance that all players in game are currently connected
    """
    game: Game
    """
    Actual game instance
    """

    class Config:
        arbitrary_types_allowed = True


class QueueState(BaseModel):
    """
    Represents a queue's current state

    As sent to the client (see responses.QueueStates)
    """

    qid: str
    """id of the queue"""
    active: bool
    """if the queue is still active"""
    gmid: str
    """game mode id"""
    users: list[core.User]
    """List of the users in the queue"""
