from enum import Enum, auto
from pydantic import BaseModel

from src.core import PointModel, Pos


class TileModel(BaseModel):
    id: str
    coord: PointModel
    owner: str | None
    """Only store the username of the owner"""
    occupation: int


class TileStateModel(BaseModel):
    id: str
    coord: PointModel | None = None
    owner: str | None = None
    occupation: int | None = None


class FactoryModel(BaseModel):
    id: str
    coord: PointModel
    alive: bool


class FactoryStateModel(BaseModel):
    id: str
    coord: PointModel | None = None
    alive: bool | None = None


class ProbeModel(BaseModel):
    id: str
    pos: PointModel
    alive: bool
    target: PointModel


class ProbeStateModel(BaseModel):
    id: str
    pos: PointModel | None = None
    alive: bool | None = None
    target: PointModel | None = None


class ProbePolicy(Enum):
    FARM = auto()
    ATTACK = auto()
