from pydantic import BaseModel

from src.models.core import core


class TileState(BaseModel):
    id: str
    coord: core.Point | None = None
    owner: str | None = None
    """Only store the username of the owner"""
    occupation: int | None = None


class FactoryState(BaseModel):
    id: str
    coord: core.Point | None = None
    death: str | None = None


class ProbeState(BaseModel):
    id: str
    pos: core.Point | None = None
    death: str | None = None
    target: core.Point | None = None
    policy: str | None = None
    """May be: Farm or Attack"""


class TurretState(BaseModel):
    id: str
    coord: core.Point | None = None
    death: str | None = None
    shot_id: str | None = None
