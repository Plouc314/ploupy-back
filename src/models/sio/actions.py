from pydantic import BaseModel

from src.models.core import core


class CreateQueue(BaseModel):
    gmid: str
    """game mode id"""
    metadata: core.GameMetadata


class JoinQueue(BaseModel):
    qid: str


class LeaveQueue(BaseModel):
    qid: str


class GameState(BaseModel):
    gid: str


class SendQueueInvitation(BaseModel):
    qid: str
    uid: str


class DisconnectBot(BaseModel):
    bot_uid: str


class ResignGame(BaseModel):
    gid: str


class BuildFactory(BaseModel):
    gid: str
    coord: core.Point
    """Coordinate where to build the factory"""


class BuildTurret(BaseModel):
    gid: str
    coord: core.Point
    """Coordinate where to build the turret"""


class MoveProbes(BaseModel):
    gid: str
    ids: list[str]
    """List of the ids of each probe to move"""
    target: core.Point
    """Coordinate of the target"""


class ExplodeProbes(BaseModel):
    gid: str
    ids: list[str]
    """List of the ids of each probe to explode"""


class ProbesAttack(BaseModel):
    gid: str
    ids: list[str]
    """List of the ids of each probe that will attack"""


class AcquireTech(BaseModel):
    gid: str
    tech: str
    """Tech name"""
