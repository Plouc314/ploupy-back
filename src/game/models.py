import numpy as np
from pydantic import BaseModel

Coord = list | tuple | np.ndarray

Pos = list | tuple | np.ndarray


class Point2D(BaseModel):
    x: float
    y: float

    @property
    def coord(self) -> np.ndarray:
        """
        Return the point as coordinate (int dtype)
        """
        return np.array([self.x, self.y], dtype=int)

    @property
    def pos(self) -> np.ndarray:
        """
        Return the point as position (float dtype)
        """
        return np.array([self.x, self.y], dtype=float)


class PlayerStateClient(BaseModel):
    username: str
    position: Point2D


class PlayerStateServer(BaseModel):
    username: str
    position: Point2D
    score: int
    tiles: list[Point2D]


class GameConfig(BaseModel):
    dim: Point2D
