from __future__ import annotations
from typing import TYPE_CHECKING

from src.core import PointModel, Coord
from src.sio import Job

from src.game.models import GameStateModel, MapStateModel, PlayerStateModel
from src.game.geometry import expansion

from .entity import Entity
from .models import FactoryModel, FactoryStateModel, TileStateModel

if TYPE_CHECKING:
    from src.game import Player, Map


class Factory(Entity):

    def __init__(self, player: "Player", coord: Coord):
        super().__init__(coord)
        self.player = player

    async def expand_job(self, map: Map):
        '''
        '''
        await Job.sleep(1)
        
        tiles = self._get_expansion_tiles(map, 1)
        yield GameStateModel(map=MapStateModel(tiles=tiles))

        await Job.sleep(1)

        tiles = self._get_expansion_tiles(map, 2)
        yield GameStateModel(map=MapStateModel(tiles=tiles))

        await Job.sleep(1)

        tiles = self._get_expansion_tiles(map, 3)
        yield GameStateModel(map=MapStateModel(tiles=tiles))


    def _get_expansion_tiles(self, map: Map, scope: int) -> list[TileStateModel]:
        '''
        Return the tiles to expand on
        '''
        tiles: list[TileStateModel] = []

        coords = expansion(self.coord, scope)
        
        for coord in coords:
            tile = map.get_tile(*coord)
            if tile is None:
                continue
            
            tile.claim(self.player)

            tiles.append(TileStateModel(**tile.model.dict()))

        return tiles

    @property
    def model(self) -> FactoryModel:
        return FactoryModel(coord=PointModel.from_list(self._pos))
