from __future__ import annotations
import numpy as np
from pydantic import BaseModel

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.core import Pos, Coord

if TYPE_CHECKING:
    from src.game.player import Player


class Entity(ABC):
    def __init__(self, player: "Player", pos: Pos | Coord):
        self.player = player
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
