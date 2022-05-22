from __future__ import annotations
from typing import TYPE_CHECKING

from src.core import PointModel, Coord
from src.sio import JobManager

from src.game.models import GameStateModel, MapStateModel, BuildProbeResponse
from src.game.geometry import expansion

from .entity import Entity
from .models import FactoryModel, FactoryStateModel, TileStateModel

if TYPE_CHECKING:
    from src.game import Player, Map


class Factory(Entity):
    def __init__(self, player: "Player", coord: Coord):
        super().__init__(coord)
        self.player = player
        self.alive = True

    async def job_expand(self, map: "Map"):
        """
        Expand the occupation next to the factory in 3 stages
        """
        await JobManager.sleep(0.5)

        tiles = self._get_expansion_tiles(map, 1)
        yield GameStateModel(map=MapStateModel(tiles=tiles))

        await JobManager.sleep(0.5)

        tiles = self._get_expansion_tiles(map, 2)
        yield GameStateModel(map=MapStateModel(tiles=tiles))

        await JobManager.sleep(0.5)

        tiles = self._get_expansion_tiles(map, 3)
        yield GameStateModel(map=MapStateModel(tiles=tiles))

    async def job_probe(self, map: "Map", jb: JobManager):
        """
        Create Probe instances at regular intervals
        """
        while self.alive:
            await JobManager.sleep(1)
            pos = self.coord + [0, 1]
            probe = self.player.build_probe(PointModel.from_list(pos))
            probe.set_target([0, 0])

            yield BuildProbeResponse(
                username=self.player.user.username, probe=probe.model
            )

    def _get_expansion_tiles(self, map: "Map", scope: int) -> list[TileStateModel]:
        """
        Return the tiles to expand on
        """
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
        return FactoryModel(
            id=self.id, coord=PointModel.from_list(self._pos), alive=self.alive
        )
