from pydantic import BaseModel

from src.core import PointModel, ResponseModel, UserModel


class ActionCreateQueueModel(BaseModel):
    n_player: int


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


class QueueStateResponse(ResponseModel):
    qid: str
    """id of the queue"""
    active: bool
    """if the queue is still active"""
    n_player: int
    users: list[UserModel]
    """List of the users in the queue"""
