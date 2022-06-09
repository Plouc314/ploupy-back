from __future__ import annotations
import random
import uuid
import numpy as np
from typing import TYPE_CHECKING

from src.core import PointModel, Coord
from src.sio import JobManager

from src.game.models import (
    GameStateModel,
    PlayerStateModel,
    TurretFireProbeResponse,
)

from .entity import Entity
from .models import (
    ProbeStateModel,
    TurretModel,
    TurretStateModel,
)

if TYPE_CHECKING:
    from src.game import Player, Map
    from .probe import Probe


class Turret(Entity):
    def __init__(self, player: Player, coord: Coord):
        super().__init__(coord)
        self.player = player
        self.game = player.game
        self.config = player.config
        self.alive = True

        # jobs flags
        self._active_jobs = {
            "fire": [],
        }

    def stop(self):
        """
        Stop whatever the turret was doing
        - Terminate all the active jobs
        """
        # reset jobs flags
        for key in self._active_jobs.keys():
            self._active_jobs[key] = []

    def die(self, notify_client: bool = True):
        """
        Make the turret die
        Notify dependencies of the turret

        If `notify_client` is true,
        send the turret state to the client (require to start a job)
        """
        if not self.alive:
            return
        self.alive = False

        self.stop()

        if self in self.player.turrets:
            self.player.turrets.remove(self)

        if notify_client:
            self.player.job_manager.send(
                "game_state",
                GameStateModel(
                    players=[
                        PlayerStateModel(
                            username=self.player.username,
                            turrets=[TurretStateModel(id=self.id, alive=False)],
                        )
                    ]
                ),
            )

    def get_income(self) -> float:
        """
        Compute the expenses of the turret (negative value)
        """
        return -self.config.turret_maintenance_costs

    def _get_fired_probe(self) -> Probe | None:
        """
        Select to the probe to fire at, if any
        """
        probes: list[Probe] = []
        for player in self.game.players.values():
            if player is self.player:
                continue
            probes += player.probes

        random.shuffle(probes)

        for probe in probes:
            pos = probe.get_current_pos()
            dist = np.linalg.norm(pos - self.pos)
        
            # check if the probe is close enough
            if dist <= self.config.turret_scope:
                return probe
        return None

    async def job_fire(self):
        """
        Fire at closest opponent probe at regular intervals
        """
        # create a unique id for the job
        jid = uuid.uuid4().hex
        # register job
        self._active_jobs["fire"].append(jid)

        while True:

            await JobManager.sleep(self.config.turret_fire_delay)

            # stop condition
            if not jid in self._active_jobs["fire"]:
                return

            # select probe
            probe = self._get_fired_probe()

            if probe is None:
                continue

            # kill probe
            probe.die(notify_client=False)

            yield TurretFireProbeResponse(
                username=self.player.username,
                turret_id=self.id,
                probe=ProbeStateModel(id=probe.id),
            )

    @property
    def model(self) -> TurretModel:
        return TurretModel(
            id=self.id, coord=PointModel.from_list(self._pos), alive=self.alive
        )
