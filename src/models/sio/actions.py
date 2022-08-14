from pydantic import BaseModel

from src.models.core import core


class CreateQueue(BaseModel):
    gmid: str
    """game mode id"""


class JoinQueue(BaseModel):
    qid: str


class LeaveQueue(BaseModel):
    qid: str


class GameState(BaseModel):
    gid: str


class SendQueueInvitation(BaseModel):
    qid: str
    uid: str


class ResignGame(BaseModel):
    pass


class BuildFactory(BaseModel):
    coord: core.Point
    """Coordinate where to build the factory"""


class BuildTurret(BaseModel):
    coord: core.Point
    """Coordinate where to build the turret"""


class MoveProbes(BaseModel):
    ids: list[str]
    """List of the ids of each probe to move"""
    target: core.Point
    """Coordinate of the target"""


class ExplodeProbes(BaseModel):
    ids: list[str]
    """List of the ids of each probe to explode"""


class ProbesAttack(BaseModel):
    ids: list[str]
    """List of the ids of each probe that will attack"""
