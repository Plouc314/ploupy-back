import numpy as np
from pydantic import BaseModel
from typing import TYPE_CHECKING

from src.core import PointModel, Pos

from .entity import Entity
from .models import ProbeModel

if TYPE_CHECKING:
    from src.game import Player


class Probe(Entity):
    
    def __init__(self, player: "Player", pos: Pos):
        super().__init__(pos)
        self.player = player


    @property
    def model(self) -> ProbeModel:
        return ProbeModel(pos=PointModel.from_list(self._pos))