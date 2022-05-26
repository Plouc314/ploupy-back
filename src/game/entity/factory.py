from __future__ import annotations
from typing import TYPE_CHECKING

from src.core import PointModel, Coord
from src.sio import JobManager

from src.game.models import GameStateModel, MapStateModel, BuildProbeResponse
from src.game.geometry import Geometry

from .entity import Entity
from .models import FactoryModel, FactoryStateModel, TileStateModel

if TYPE_CHECKING:
    from src.game import Player, Map
    from .probe import Probe


class Factory(Entity):
    def __init__(self, player: "Player", coord: Coord):
        super().__init__(coord)
        self.player = player
        self.config = self.player.config
        self.alive = True
        
        # probes created by the factory
        self._probes: list[Probe] = []

    def remove_prove(self, probe: Probe):
        '''
        Remove a probe from the "ownership" of the factory
        i.e. calling this func will allow the factory to produce
        one more probe.
        '''
        if probe in self._probes:
            self._probes.remove(probe)

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
            
            await JobManager.sleep(2)
            
            # check that the number of probes doesn't exceed the maximum
            if len(self._probes) == self.config.factory_max_probe:
                continue
            
            pos = self.coord + [0, 1]
            probe = self.player.build_probe(PointModel.from_list(pos))

            # TEMP set probe first target BEFORE sending probe model
            target = self.player.get_probe_farm_target(probe)
            if target is not None:
                probe.set_target(target)

            probe.factory = self            
            self._probes.append(probe)

            # start probe job
            job_move = jb.make_job("game_state", probe.job_move)
            job_move.start(map)

            yield BuildProbeResponse(
                username=self.player.user.username, probe=probe.model
            )

    def _get_expansion_tiles(self, map: "Map", scope: int) -> list[TileStateModel]:
        """
        Return the tiles to expand on
        """
        tiles: list[TileStateModel] = []

        coords = Geometry.square(self.coord, scope)

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
