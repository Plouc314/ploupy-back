from __future__ import annotations
import numpy as np
import time
import uuid
from typing import TYPE_CHECKING

from src.core import PointModel, Pos, Coord
from src.sio import JobManager

from src.game.models import (
    GameStateModel,
    PlayerStateModel,
    MapStateModel,
    TileStateModel,
)

from .entity import Entity
from .models import ProbeModel, ProbeStateModel, ProbePolicy

if TYPE_CHECKING:
    from src.game import Player, Map
    from .factory import Factory
    from .tile import Tile


class Probe(Entity):
    def __init__(self, player: "Player", pos: Pos):
        super().__init__(pos)
        self.player = player
        self.config = player.config
        self.target: Coord = self.coord
        """the probe target"""
        self.alive = True
        self.policy = ProbePolicy.FARM

        self.factory: Factory | None = None
        """The factory that created the probe"""

        # time where the probe started to move to the target
        self._departure_time: float = time.time()
        # travel time until the probe reachs the target
        self._travel_duration: float = 0
        # travel distance (unit: coord) until reaching the target
        self._travel_distance: float = 0
        # travel vector is the direction to the target (unit vector)
        self._travel_vector: np.ndarray = np.zeros((2))

        # jobs flags
        self._active_jobs = {
            "move": [],
        }

    def stop(self):
        """
        Stop whatever the probe was doing
        - Terminate all the active jobs
        - Reset probe policy

        If the "move" job is active, update the probe's position
        """
        self.policy = ProbePolicy.FARM

        if len(self._active_jobs["move"]) > 0:
            self.pos = self.get_current_pos()

        # reset jobs flags
        for key in self._active_jobs.keys():
            self._active_jobs[key] = []

    def die(self, notify_client: bool = True):
        """
        Make the probe die
        Notify dependencies of the probe

        If `notify_client` is true,
        send the probe state to the client (require to start a job)
        """
        self.alive = False

        self.stop()

        self.player.probes.remove(self)

        if self.factory is not None:
            self.factory.remove_probe(self)

        if notify_client:
            self.player.job_manager.send(
                "game_state",
                GameStateModel(
                    players=[
                        PlayerStateModel(
                            username=self.player.user.username,
                            probes=[ProbeStateModel(id=self.id, alive=False)],
                        )
                    ],
                ),
            )

    def set_policy(self, policy: ProbePolicy):
        """
        Set the probe policy
        No side effect (for now)
        """
        self.policy = policy

    def set_target(self, target: Coord):
        """
        Set the probe's target coordinate,
        will reset the probe's departure time
        """
        self._departure_time = time.time()
        self.target = np.array(target, dtype=int)

        if np.all(self.target == self.coord):
            self._travel_distance = 0
            self._travel_duration = 0
            self._travel_vector = np.zeros((2))
            return

        # compute travel time / distance / vector
        self._travel_distance = np.linalg.norm(self.target - self.pos)
        self._travel_duration = self._travel_distance / self.config.probe_speed
        self._travel_vector = (self.target - self.pos) / self._travel_distance

    def get_next_target(self) -> Coord:
        """
        Get the next target to go to,
        depending on the current probe policy
        """
        if self.policy == ProbePolicy.FARM:
            return self.player.get_probe_farm_target(self)
        elif self.policy == ProbePolicy.ATTACK:
            return self.player.get_probe_attack_target(self)
        else:
            raise NotImplementedError()

    def get_current_pos(self) -> Pos:
        """
        Return the actual position of the probe
        (somewhere between `pos` and `target`)
        """
        t = time.time() - self._departure_time
        return self.pos + self._travel_vector * self.config.probe_speed * t

    def explode(self, map: Map) -> list[Tile]:
        """
        Make the probe explodes
        Claim twice the opponent tiles in the neighbourhood
        Make the probe die (NOTE don't notify client)
        """
        # get current coord
        current = np.array(self.get_current_pos(), dtype=int)
        tile = map.get_tile(*current)
        if tile is None:
            # kill
            self.die(notify_client=False)
            return []

        tiles = [tile] + map.get_neighbour_tiles(tile)
        reached_tiles = []

        for tile in tiles:
            if tile.owner is not None and tile.owner is not self.player:
                tile.claim(self.player)
                tile.claim(self.player)
                reached_tiles.append(tile)

        # kill
        self.die(notify_client=False)

        return reached_tiles

    def behave(self, map: Map) -> GameStateModel | None:
        """
        Execute what the probe has to do when its arrive on a tile
        depending on the current policy
        """
        tile = map.get_tile(*self.coord)

        if self.policy == ProbePolicy.FARM:

            tile.claim(self.player)

            return GameStateModel(
                map=MapStateModel(tiles=[tile.get_state()]),
                players=[
                    PlayerStateModel(
                        username=self.player.user.username,
                        probes=[
                            ProbeStateModel(
                                id=self.id, pos=PointModel.from_list(self.pos)
                            )
                        ],
                    )
                ],
            )

        elif self.policy == ProbePolicy.ATTACK:

            if tile.owner is None or tile.owner is self.player:
                return None

            tiles = self.explode(map)

            return GameStateModel(
                map=MapStateModel(tiles=[tile.get_state() for tile in tiles]),
                players=[
                    PlayerStateModel(
                        username=self.player.user.username,
                        probes=[ProbeStateModel(id=self.id, alive=self.alive)],
                    )
                ],
            )
        else:
            raise NotImplementedError()

    async def job_move(self, map: "Map"):
        """
        Make the probe move to a target, wait, choose a new target, ...
        """

        # create a unique id for the job
        jid = uuid.uuid4().hex
        # register job
        self._active_jobs["move"].append(jid)

        while True:

            # wait for the probe to reach destination
            sleep = self._travel_duration - (time.time() - self._departure_time)
            if sleep > 0:
                await JobManager.sleep(sleep)

            # stop condition
            if not jid in self._active_jobs["move"]:
                return

            # set target as new position
            self.coord = self.target

            # reset travel vector -> stabilise get_current_pos
            self._travel_vector = np.zeros((2))

            response = self.behave(map)

            if response is not None:
                yield response

            await JobManager.sleep(0.5 if self.policy == ProbePolicy.FARM else 0)

            # stop condition
            if not jid in self._active_jobs["move"]:
                return

            # get new target
            target = self.get_next_target()
            self.set_target(target)

            # assert that the probe can attack a tile if in attack policy
            if self.policy == ProbePolicy.ATTACK:
                # if no tile to attack -> fall back to farm policy
                if np.all(self.coord == target):
                    self.policy = ProbePolicy.FARM

            yield GameStateModel(
                players=[
                    PlayerStateModel(
                        username=self.player.user.username,
                        probes=[
                            ProbeStateModel(
                                id=self.id, target=PointModel.from_list(self.target)
                            )
                        ],
                    )
                ]
            )

    def get_state(self) -> ProbeStateModel:
        """
        Return the probe state (position and target)
        """
        return ProbeStateModel(
            id=self.id,
            pos=PointModel.from_list(self.get_current_pos()),
            target=PointModel.from_list(self.target),
        )

    @property
    def model(self) -> ProbeModel:
        return ProbeModel(
            id=self.id,
            pos=PointModel.from_list(self.get_current_pos()),
            target=PointModel.from_list(self.target),
            alive=self.alive,
        )
