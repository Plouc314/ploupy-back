import numpy as np
from pydantic import BaseModel

Coord = list | tuple | np.ndarray

Pos = list | tuple | np.ndarray


class Point2D(BaseModel):
    x: float
    y: float

    @classmethod
    def from_list(cls, point: Pos | Coord) -> "Point2D":
        '''
        Build an instance of Point2D from a list
        '''
        return Point2D(x=point[0], y=point[1])

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
    position: Point2D


class PlayerStateServer(BaseModel):
    username: str
    position: Point2D
    score: int
    tiles: list[Point2D]


class GameConfig(BaseModel):
    dim: Point2D


class GameStateServer(BaseModel):
    dim: Point2D
    players: list[PlayerStateServer]