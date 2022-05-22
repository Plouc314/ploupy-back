from pydantic import BaseModel

from src.core import PointModel


class ActionBuildFactoryModel(BaseModel):
    coord: PointModel
