import numpy as np

from src.core import Coord

from .tile import Tile

class Map:

    def __init__(self, dim: Coord):
        self.dim = np.array(dim, dtype=int)
        self.tiles: list[list[Tile]] = None
        self._build_tiles()

    def _build_tiles(self) -> None:
        '''
        Generate tiles with default values
        '''
        self.tiles = []
        for x in range(self.dim[0]):
            col = []
            for y in range(self.dim[1]):
                tile = Tile((x, y))
                col.append(tile)
            self.tiles.append(col)
    
    def get_tile(self, x: int, y: int) -> Tile | None:
        '''
        Return the tile at the given coordinate,
        or None if they're invalid
        '''
        if 0 <= x < self.dim[0] and 0 <= y < self.dim[1]:
            return self.tiles[x][y]
        return None
    
    