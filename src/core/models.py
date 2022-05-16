import numpy as np
from pydantic import BaseModel


class UserModel(BaseModel):
    """
    Represent a user as stored in the db
    """

    uid: str = ""
    username: str = ""
    email: str = ""


Coord = list | tuple | np.ndarray
Pos = list | tuple | np.ndarray


class PointModel(BaseModel):
    """
    Represent a point in 2D
    """

    x: float
    y: float

    @classmethod
    def from_list(cls, point: Pos) -> "PointModel":
        """
        Build an instance of PointModel from a list
        """
        return PointModel(x=point[0], y=point[1])

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


class ResponseModel(BaseModel):
    """
    Represent a response from a server (api/sio)
    """

    success: bool = True
    msg: str = ""
