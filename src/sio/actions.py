from pydantic import BaseModel

from src.core import PointModel


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
