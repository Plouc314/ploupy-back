import numpy as np
from pydantic import BaseModel

from src.core import PointModel

from .entity import Entity


class FactoryModel(BaseModel):
    coord: PointModel


class Factory(Entity):
    @property
    def model(self) -> FactoryModel:
        return FactoryModel(coord=PointModel.from_list(self._pos))
