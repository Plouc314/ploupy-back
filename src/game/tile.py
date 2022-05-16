import numpy as np

from src.core import Coord
from src.game.entity import Building


class Tile:

    def __init__(self, coord: Coord):
        self.coord = np.array(coord, dtype=int)
        self.building: Building | None = None
    

