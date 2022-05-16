import numpy as np
from pydantic import BaseModel

from src.core import PointModel

from .entity import Entity


class ProbeModel(BaseModel):
    pos: PointModel


class Probe(Entity):
    
    @property
    def model(self) -> ProbeModel:
        return ProbeModel(pos=PointModel.from_list(self._pos))