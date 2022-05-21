import numpy as np
from pydantic import BaseModel

from abc import ABC, abstractmethod

from src.core import Pos, Coord


class Entity(ABC):
    def __init__(self, pos: Pos | Coord):
        self._pos = np.array(pos, dtype=float)

    @property
    def coord(self) -> np.ndarray:
        """
        Return the coordinate (int dtype)
        """
        return self._pos.astype(int)

    @coord.setter
    def coord(self, value: Coord):
        self._pos = np.array(value, dtype=float)

    @property
    def pos(self) -> np.ndarray:
        """
        Return the position (float dtype)
        """
        return self._pos.astype(float)

    @pos.setter
    def pos(self, value: Pos):
        self._pos = np.array(value, dtype=float)

    @property
    @abstractmethod
    def model(self) -> BaseModel:
        """
        Return the model (pydantic) representation of the instance
        """
