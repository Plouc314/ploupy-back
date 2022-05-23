import numpy as np

from src.game.entity.tile import Tile

from .models import MapModel, GameConfig
from .geometry import Geometry

class Map:
    def __init__(self, config: GameConfig):
        self.config = config
        self.dim = np.array(config.dim.coord, dtype=int)
        self._tiles_2d: list[list[Tile]] = None
        self._tiles_map: dict[str, Tile] = None
        self._build_tiles()

    def _build_tiles(self) -> None:
        """
        Generate tiles with default values
        """
        self._tiles_2d = []
        self._tiles_map = {}
        for x in range(self.dim[0]):
            col = []
            for y in range(self.dim[1]):
                tile = Tile((x, y), self.config)
                col.append(tile)
                self._tiles_map[tile.id] = tile
            self._tiles_2d.append(col)

    def get_tile(self, x: int, y: int) -> Tile | None:
        """
        Return the tile at the given coordinate,
        or None if they're invalid
        """
        if 0 <= x < self.dim[0] and 0 <= y < self.dim[1]:
            return self._tiles_2d[x][y]
        return None

    def get_neighbour_tiles(self, tile: Tile) -> list[Tile]:
        '''
        Return the tiles that are neighbour of the `tile`
        
        Neighbours as defined by `Geometry.ring(coord, 1)`
        '''
        tile = self._tiles_map.get(id, None)
        if tile is None:
            return []
        
        coords = Geometry.ring(tile.coord, 1)
        neighbours = []

        for coord in coords:
            neighbour = self.get_tile(*coord)
            if neighbour is not None:
                neighbours.append(neighbour)
        return neighbours

    @property
    def model(self) -> MapModel:
        """
        Return the model (pydantic) representation of the instance
        """
        tiles: list[Tile] = []
        for col in self._tiles_2d:
            tiles.extend(col)
        return MapModel(tiles=[tile.model for tile in tiles])
