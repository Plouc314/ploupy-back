from __future__ import annotations
import numpy as np
import time
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
from .models import ProbeModel, ProbeStateModel

if TYPE_CHECKING:
    from src.game import Player, Map


class Probe(Entity):
    def __init__(self, player: "Player", pos: Pos):
        super().__init__(pos)
        self.player = player
        self.config = player.config
        self.target: Coord = self.coord
        """the probe target"""
        self.alive = True

        # time where the probe started to move to the target
        self._departure_time: float = time.time()
        # travel time until the probe reachs the target
        self._travel_duration: float = 0
        # travel distance (unit: coord) until reaching the target
        self._travel_distance: float = 0
        # travel vector is the direction to the target (unit vector)
        self._travel_vector: np.ndarray = np.zeros((2))

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
        self._travel_distance = np.linalg.norm(self.target - self.coord)
        self._travel_duration = self._travel_distance / self.config.probe_speed
        self._travel_vector = (self.target - self.coord) / self._travel_distance

    def _get_new_target(self) -> Coord:
        """
        Select the next target for the probe
        """
        return self.player.get_probe_target(self)

    def get_current_pos(self) -> Pos:
        """
        Return the actual position of the probe
        (somewhere between `pos` and `target`)
        """
        t = time.time() - self._departure_time
        return self.pos + self._travel_vector * t

    async def job_move(self, map: "Map"):
        """ """
        while self.alive:

            # wait for the probe to reach destination
            sleep = self._travel_duration - (time.time() - self._departure_time)
            if sleep > 0:
                await JobManager.sleep(sleep)

            # set target as new position
            self.coord = self.target

            # claim tile
            tile = map.get_tile(*self.coord)
            tile.claim(self.player)

            yield GameStateModel(
                map=MapStateModel(
                    tiles=[tile.get_state()]
                ),
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

            await JobManager.sleep(0.5)

            # get new target
            target = self._get_new_target()
            self.set_target(target)

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

    @property
    def model(self) -> ProbeModel:
        return ProbeModel(
            id=self.id,
            pos=PointModel.from_list(self.get_current_pos()),
            target=PointModel.from_list(self.target),
            alive=self.alive,
        )
