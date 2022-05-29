from __future__ import annotations
import uuid
from typing import TYPE_CHECKING

from src.core import PointModel, Coord
from src.sio import JobManager

from src.game.models import (
    GameStateModel,
    MapStateModel,
    BuildProbeResponse,
    PlayerStateModel,
)
from src.game.geometry import Geometry

from .entity import Entity
from .models import FactoryModel, FactoryStateModel, ProbeStateModel, TileStateModel

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

        # jobs flags
        self._active_jobs = {
            "expand": [],
            "probe": [],
        }

    def stop(self):
        """
        Stop whatever the factory was doing
        - Terminate all the active jobs
        """
        # reset jobs flags
        for key in self._active_jobs.keys():
            self._active_jobs[key] = []

    def die(self, notify_client: bool = True) -> list[Probe]:
        """
        Make the factory die
        Notify dependencies of the factory
        Try to transfer factory probes to other factories

        If `notify_client` is true,
        send the factory state to the client (require to start a job)

        Return the list of probes that died (the ones that counldn't be transfered)
        """
        self.alive = False

        self.stop()

        self.player.factories.remove(self)

        # try to transfer existing probes to other factories
        for factory in self.player.factories:

            # transfer as much probes as possible
            while len(self._probes) > 0:
                probe = self._probes.pop()
                if not factory.receive_probe(probe):
                    self._probes.append(probe) # add the probe back
                    break

        # kill other probes
        probes = self._probes.copy()
        states = []
        for probe in probes:
            probe.die(notify_client=False)
            states.append(ProbeStateModel(id=probe.id, alive=probe.alive))

        if notify_client:
            self.player.job_manager.send(
                "game_state",
                GameStateModel(
                    players=[
                        PlayerStateModel(
                            username=self.player.user.username,
                            probes=states,
                            factories=[FactoryStateModel(id=self.id, alive=False)],
                        )
                    ]
                ),
            )

        return probes

    def receive_probe(self, probe: Probe) -> bool:
        """
        Add a probe to the "ownership" of the factory
        i.e. calling this func will prevent the factory from producing
        one more probe.
        Return if the factory can receive the probe or not.
        """
        if len(self._probes) == self.config.factory_max_probe:
            return False
        if probe in self._probes:
            self._probes.append(probe)

        return True

    def remove_probe(self, probe: Probe):
        """
        Remove a probe from the "ownership" of the factory
        i.e. calling this func will allow the factory to produce
        one more probe.
        """
        if probe in self._probes:
            self._probes.remove(probe)

    async def job_expand(self, map: "Map"):
        """
        Expand the occupation next to the factory in 3 stages
        """
        # create a unique id for the job
        jid = uuid.uuid4().hex
        # register job
        self._active_jobs["expand"].append(jid)

        for i in range(1, 4):
            await JobManager.sleep(0.5)

            # stop condition
            if not jid in self._active_jobs["expand"]:
                return

            tiles = self._get_expansion_tiles(map, i)
            yield GameStateModel(map=MapStateModel(tiles=tiles))

    async def job_probe(self, map: "Map", jb: JobManager):
        """
        Create Probe instances at regular intervals
        """

        # create a unique id for the job
        jid = uuid.uuid4().hex
        # register job
        self._active_jobs["probe"].append(jid)

        while True:

            await JobManager.sleep(self.config.factory_build_probe_delay)

            # stop condition
            if not jid in self._active_jobs["probe"]:
                return

            # check that the number of probes doesn't exceed the maximum
            if len(self._probes) == self.config.factory_max_probe:
                continue

            probe = self.player.build_probe(PointModel.from_list(self.coord))

            # check that there was enough money to build the probe
            if probe is None:
                continue

            # set probe first target BEFORE sending probe model
            target = self.player.get_probe_farm_target(probe)
            if target is not None:
                probe.set_target(target)

            probe.factory = self
            self._probes.append(probe)

            # start probe job
            job_move = jb.make_job("game_state", probe.job_move)
            job_move.start(map)

            yield BuildProbeResponse(
                username=self.player.user.username,
                money=self.player.money,
                probe=probe.model,
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
