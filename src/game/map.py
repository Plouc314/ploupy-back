import numpy as np

from .tile import Tile
from .models import Coord

class Map:

    def __init__(self, dim: Coord):
        self.dim = np.array(dim, dtype=int)
        self.tiles: list[list[Tile]] = None

    def _build_tiles(self) -> None:
        '''
        Generate tiles with default values
        '''
        for x in range(self.dim.shape[0]):
            col = []
            for y in range(self.dim.shape[1]):
                tile = Tile((x, y))
                col.append(tile)
            self.tiles.append(col)
    
    def get_tile(self, x: int, y: int) -> Tile | None:
        '''
        Return the tile at the given coordinate,
        or None if they're invalid
        '''
        if 0 <= x < self.dim.shape[0] and 0 <= y < self.dim.shape[1]:
            return self.tiles[x][y]
        return None