from __future__ import annotations
import numpy as np
import time
from typing import TYPE_CHECKING

from src.core import PointModel, Pos, Coord
from src.sio import JobManager

from .entity import Entity
from .models import ProbeModel

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

    def set_target(self, target: Coord):
        """
        Set the probe's target coordinate,
        will reset the probe's departure time
        """
        self._departure_time = time.time()
        self.target = np.array(target, dtype=int)

        # compute travel time / distance
        self._travel_distance = np.linalg.norm(self.target - self.coord)
        self._travel_duration = self._travel_distance / self.config.probe_speed

    async def job_move(self, map: "Map"):
        """ """
        while self.alive:
            await JobManager.sleep(1)
            if time.time() - self._departure_time > self._travel_duration:
                coord = np.random.randint(0, map.dim[0], 2)

    @property
    def model(self) -> ProbeModel:
        return ProbeModel(
            id=self.id,
            pos=PointModel.from_list(self._pos),
            target=PointModel.from_list(self.target),
            alive=self.alive,
        )
