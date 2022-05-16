from pydantic import BaseModel

from src.core import PointModel


class ActionBuildModel(BaseModel):
    coord: PointModel
