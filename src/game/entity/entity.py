import uuid
import numpy as np
from pydantic import BaseModel
from abc import ABC, abstractmethod

from models import core as _c


class Entity(ABC):
    def __init__(self, pos: _c.Pos | _c.Coord, id: str | None = None):
        self._pos = np.array(pos, dtype=float)
        self.id = uuid.uuid4().hex if id is None else id

    @property
    def coord(self) -> np.ndarray:
        """
        Return the coordinate (int dtype)
        """
        return self._pos.astype(int)

    @coord.setter
    def coord(self, value: _c.Coord):
        self._pos = np.array(value, dtype=float)

    @property
    def pos(self) -> np.ndarray:
        """
        Return the position (float dtype)
        """
        return self._pos.astype(float)

    @pos.setter
    def pos(self, value: _c.Pos):
        self._pos = np.array(value, dtype=float)

    @property
    @abstractmethod
    def model(self) -> BaseModel:
        """
        Return the model (pydantic) representation of the instance
        """
