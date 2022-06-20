from enum import Enum, auto
from pydantic import BaseModel

from models.core import core


class Tile(BaseModel):
    id: str
    coord: core.Point
    owner: str | None
    """Only store the username of the owner"""
    occupation: int


class TileState(BaseModel):
    id: str
    coord: core.Point | None = None
    owner: str | None = None
    occupation: int | None = None


class Factory(BaseModel):
    id: str
    coord: core.Point
    alive: bool


class FactoryState(BaseModel):
    id: str
    coord: core.Point | None = None
    alive: bool | None = None


class Probe(BaseModel):
    id: str
    pos: core.Point
    alive: bool
    target: core.Point


class ProbeState(BaseModel):
    id: str
    pos: core.Point | None = None
    alive: bool | None = None
    target: core.Point | None = None


class ProbePolicy(Enum):
    FARM = auto()
    ATTACK = auto()


class Turret(BaseModel):
    id: str
    coord: core.Point
    alive: bool


class TurretState(BaseModel):
    id: str
    coord: core.Point | None = None
    alive: bool | None = None

