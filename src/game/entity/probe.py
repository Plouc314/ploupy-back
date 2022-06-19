from __future__ import annotations
import numpy as np
import time
import uuid
from typing import TYPE_CHECKING

from models import core as _c, game as _g
from sio import JobManager

from .entity import Entity

if TYPE_CHECKING:
    from game import Player, Map
    from .factory import Factory
    from .tile import Tile


class Probe(Entity):
    def __init__(self, player: "Player", pos: _c.Pos):
        super().__init__(pos)
        self.player = player
        self.config = player.config

        # the probe target
        self.target: _c.Coord = self.coord

        self.alive = True
        self.policy = _g.ProbePolicy.FARM

        # the factory that created the probe
        self.factory: Factory | None = None

        # if the probe is currently claiming a tile
        # used on farm policy to avoid claiming to fast when
        # manually moving the probe
        self.is_claiming = False

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
        self.policy = _g.ProbePolicy.FARM

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
        if not self.alive:
            return
        self.alive = False

        self.stop()

        if self in self.player.probes:
            self.player.probes.remove(self)

        if self.factory is not None:
            self.factory.remove_probe(self)

        if notify_client:
            self.player.job_manager.send(
                "game_state",
                _g.GameState(
                    players=[
                        _g.PlayerState(
                            username=self.player.username,
                            probes=[_g.ProbeState(id=self.id, alive=False)],
                        )
                    ],
                ),
            )

    def set_policy(self, policy: _g.ProbePolicy):
        """
        Set the probe policy
        No side effect (for now)
        """
        self.policy = policy

    def set_target(self, target: _c.Coord):
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

    def get_next_target(self) -> _c.Coord:
        """
        Get the next target to go to,
        depending on the current probe policy
        """
        if self.policy == _g.ProbePolicy.FARM:
            return self.player.get_probe_farm_target(self)
        elif self.policy == _g.ProbePolicy.ATTACK:
            return self.player.get_probe_attack_target(self)
        else:
            raise NotImplementedError()

    def get_current_pos(self) -> _c.Pos:
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

    def _behave_farm(self, tile: Tile, map: Map) -> _g.GameState | None:
        """
        Actions of the probe when arriving on a tile on farm policy
        """
        # in case the probe is currently claiming, do nothing
        # this may happen when manually moving the probe thus
        # having temporarily two job_move active
        if self.is_claiming:
            return None

        # set the is claiming flag -> will be up until end of claiming delay
        self.is_claiming = True

        tile.claim(self.player)

        return _g.GameState(
            map=_g.MapState(tiles=[tile.get_state()]),
            players=[
                _g.PlayerState(
                    username=self.player.username,
                    probes=[
                        _g.ProbeState(id=self.id, pos=_c.Point.from_list(self.pos))
                    ],
                )
            ],
        )

    def _behave_attack(self, tile: Tile, map: Map) -> _g.GameState | None:
        """
        Actions of the probe when arriving on a tile on attack policy
        """
        if tile.owner is None or tile.owner is self.player:
            return None

        tiles = self.explode(map)

        return _g.GameState(
            map=_g.MapState(tiles=[tile.get_state() for tile in tiles]),
            players=[
                _g.PlayerState(
                    username=self.player.username,
                    probes=[_g.ProbeState(id=self.id, alive=self.alive)],
                )
            ],
        )

    def behave(self, map: Map) -> _g.GameState | None:
        """
        Execute what the probe has to do when its arrive on a tile
        depending on the current policy
        """
        tile = map.get_tile(*self.coord)

        if self.policy == _g.ProbePolicy.FARM:
            return self._behave_farm(tile, map)
        elif self.policy == _g.ProbePolicy.ATTACK:
            return self._behave_attack(tile, map)
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

            if self.policy == _g.ProbePolicy.FARM:
                await JobManager.sleep(self.config.probe_claim_delay)

                # in case response -> the tile was claimed in this job
                # reset claiming flag -> done here in case this job
                # is no longer active
                if response is not None:
                    self.is_claiming = False

            # stop condition
            if not jid in self._active_jobs["move"]:
                return

            # get new target
            target = self.get_next_target()
            self.set_target(target)

            # assert that the probe can attack a tile if in attack policy
            if self.policy == _g.ProbePolicy.ATTACK:
                # if no tile to attack -> fall back to farm policy
                if np.all(self.coord == target):
                    self.policy = _g.ProbePolicy.FARM

            yield _g.GameState(
                players=[
                    _g.PlayerState(
                        username=self.player.username,
                        probes=[
                            _g.ProbeState(
                                id=self.id, target=_c.Point.from_list(self.target)
                            )
                        ],
                    )
                ]
            )

    def get_state(self) -> _g.ProbeState:
        """
        Return the probe state (position and target)
        """
        return _g.ProbeState(
            id=self.id,
            pos=_c.Point.from_list(self.get_current_pos()),
            target=_c.Point.from_list(self.target),
        )

    @property
    def model(self) -> _g.Probe:
        return _g.Probe(
            id=self.id,
            pos=_c.Point.from_list(self.get_current_pos()),
            target=_c.Point.from_list(self.target),
            alive=self.alive,
        )
