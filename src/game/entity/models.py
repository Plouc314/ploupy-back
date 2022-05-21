from pydantic import BaseModel

from src.core import PointModel, Pos


class TileModel(BaseModel):
    coord: PointModel
    owner: str | None
    """Only store the username of the owner"""
    occupation: int


class TileStateModel(BaseModel):
    coord: PointModel
    owner: str | None = None
    occupation: int = None


class FactoryModel(BaseModel):
    coord: PointModel


class FactoryStateModel(BaseModel):
    coord: PointModel


class ProbeModel(BaseModel):
    pos: PointModel


class ProbeStateModel(BaseModel):
    pos: PointModel
