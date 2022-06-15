from __future__ import annotations
from pydantic import BaseModel
from typing import TYPE_CHECKING

from src.core import GameModeModel, PointModel, ResponseModel, UserModel
from src.game import Game, GamePlayerStatsModel


class UserSioModel(BaseModel):
    sid: str
    """socketio id for user session"""
    user: UserModel
    gid: str | None = None
    """game id"""


class QueueSioModel(BaseModel):
    qid: str
    """queue id"""
    active: bool
    users: list[UserSioModel]
    game_mode: GameModeModel


class GameSioModel(BaseModel):
    gid: str
    """game id"""
    mode: GameModeModel
    """
    Game mode of the game
    """
    users: list[UserSioModel]
    """
    socket-io users that are currently connected
    NOTE: no assurance that all players in game are currently connected
    """
    game: Game

    class Config:
        arbitrary_types_allowed = True


class ActionCreateQueueModel(BaseModel):
    gmid: str
    """game mode id"""


class ActionJoinQueueModel(BaseModel):
    qid: str


class ActionLeaveQueueModel(BaseModel):
    qid: str


class ActionResignGameModel(BaseModel):
    pass


class ActionBuildFactoryModel(BaseModel):
    coord: PointModel
    """Coordinate where to build the factory"""


class ActionBuildTurretModel(BaseModel):
    coord: PointModel
    """Coordinate where to build the turret"""


class ActionMoveProbesModel(BaseModel):
    ids: list[str]
    """List of the ids of each probe to move"""
    targets: list[PointModel]
    """List of the coordinate of each probe target"""


class ActionExplodeProbesModel(BaseModel):
    ids: list[str]
    """List of the ids of each probe to explode"""


class ActionProbesAttackModel(BaseModel):
    ids: list[str]
    """List of the ids of each probe that will attack"""


class QueueState(BaseModel):
    qid: str
    """id of the queue"""
    active: bool
    """if the queue is still active"""
    gmid: str
    """game mode id"""
    users: list[UserModel]
    """List of the users in the queue"""


class QueueStateResponse(ResponseModel):
    queues: list[QueueState]


class GameResultsResponse(ResponseModel):
    ranking: list[UserModel]
    """players: from best (idx: 0) to worst (idx: -1)"""
    stats: list[GamePlayerStatsModel]
    mmrs: list[int]
    """
    new mmr of players in game (same order as ranking)
    """
    mmr_diffs: list[int]
    """
    mmr difference of players in game (same order as ranking)
    """
