from __future__ import annotations
import random
import uuid
import numpy as np
from typing import TYPE_CHECKING

from src.core import UserModel, PointModel, Coord
from src.sio import JobManager

from src.game.entity.models import FactoryStateModel, TurretStateModel, ProbeStateModel
from src.game.entity.factory import Factory
from src.game.entity.turret import Turret
from src.game.entity.probe import Probe
from src.game.entity.tile import Tile

from .exceptions import ActionException
from .models import (
    GameStateModel,
    MapStateModel,
    PlayerModel,
    PlayerStateModel,
    TileStateModel,
)
from .geometry import Geometry

if TYPE_CHECKING:
    from .game import Game


class Player:
    def __init__(self, user: UserModel, game: Game):
        self.user = user
        self.game = game
        self.map = game.map
        self.job_manager = game.job_manager
        self.config = game.config
        self.money = self.config.initial_money
        self.score = 0
        self.alive = True
        self.factories: list[Factory] = []
        self.turrets: list[Turret] = []
        self.probes: list[Probe] = []
        self.tiles: list[Tile] = []

        # jobs flags
        self._active_jobs: set[str] = set()

    @property
    def username(self) -> str:
        return self.user.username

    def stop(self):
        """
        Terminate all the active jobs
        """
        self._active_jobs.clear()

    def die(self, notify_client: bool = True, is_winner: bool = False):
        """
        Make the player die
        Notify dependencies of the player (factories, turrets, ...)

        If `notify_client` is true,
        send the player state to the client (require to start a job)

        If `is_winner` (and `notify_client`) are true,
        send the player state (with all factories / turrets / probes dead)
        but the player alive.
        Also, don't notify game of player's death
        """
        self.alive = False

        self.stop()

        if not is_winner:
            self.game.notify_death(self)

        factories = self.factories
        # clear factories attribute ->
        # avoid factories to look for probe transfers when dying
        self.factories = []

        probes: list[Probe] = []

        for factory in factories:
            probes += factory.die(notify_client=False, check_loose_condition=False)

        turrets = self.turrets.copy()
        for turret in turrets:
            turret.die(notify_client=False)

        if notify_client:
            self.job_manager.send(
                "game_state",
                GameStateModel(
                    players=[
                        PlayerStateModel(
                            username=self.user.username,
                            alive=is_winner,
                            factories=[
                                FactoryStateModel(id=factory.id, alive=False)
                                for factory in factories
                            ],
                            turrets=[
                                TurretStateModel(id=turret.id, alive=False)
                                for turret in turrets
                            ],
                            probes=[
                                ProbeStateModel(id=probe.id, alive=False)
                                for probe in probes
                            ],
                        )
                    ],
                ),
            )

    def loose_condition(self) -> bool:
        """
        Return if the player has lost (i.e. its loose condition is fulfilled)
        """
        return len(self.factories) == 0

    def build_factory(self, coord: PointModel) -> Factory:
        """
        Build a factory at the given coord is possible

        Update the player's money

        Raise: ActionException if not enough money
        """
        if self.money < self.config.factory_price:
            raise ActionException(f"Not enough money (<{self.config.factory_price})")

        self.money -= self.config.factory_price

        factory = Factory(self, coord.coord)
        self.factories.append(factory)
        return factory

    def build_turret(self, coord: PointModel) -> Turret:
        """
        Build a turret at the given coord is possible

        Update the player's money

        Raise: ActionException if not enough money
        """
        if self.money < self.config.turret_price:
            raise ActionException(f"Not enough money (<{self.config.turret_price})")

        self.money -= self.config.turret_price

        turret = Turret(self, coord.coord)
        self.turrets.append(turret)
        return turret

    def build_probe(self, pos: PointModel) -> Probe | None:
        """
        Build a probe at the given position (no check on position)
        if enough money, else return None
        """
        if self.money <= self.config.probe_price:
            return None
        self.money -= self.config.probe_price

        probe = Probe(self, pos.pos)
        self.probes.append(probe)
        return probe

    def add_tile(self, tile: Tile) -> None:
        """
        Add a tile to the player

        NOTE: should only be called inside `Tile.claim` to keep the player & tile
        synchronized.
        """
        if not tile in self.tiles:
            self.tiles.append(tile)

    def remove_tile(self, tile: Tile) -> None:
        """
        Remove a tile from the player

        NOTE: should only be called inside `Tile.claim` to keep the player & tile
        synchronized.
        """
        if tile in self.tiles:
            self.tiles.remove(tile)

    def get_probe(self, id: str) -> Probe | None:
        """
        Return the probe with the given `id` if it exists, else None
        """
        for probe in self.probes:
            if probe.id == id:
                return probe
        return None

    def _get_probe_farm_target(self, coord: Coord) -> Coord | None:
        """
        Return a possible target to farm (own or unoccupied tile)
        in the surroundings of `coord` or None
        """
        poss = list(Geometry.square(coord, 3))
        poss.remove(tuple(coord))
        random.shuffle(poss)

        for coord in poss:
            tile = self.map.get_tile(*coord)
            if tile is None:
                continue

            # check if tile occupied by an other player
            if tile.owner is not self and tile.occupation > 3:
                continue

            # check if tile occupation full
            if tile.occupation == self.config.max_occupation:
                continue

            # check if tile is isolated
            if tile.owner is not self and tile.occupation < 3:
                neighbours = self.map.get_neighbour_tiles(tile)
                for neighbour in neighbours:
                    if neighbour.owner is self:
                        break
                else:
                    continue

            return coord

        return None

    def get_probe_farm_target(self, probe: Probe) -> Coord:
        """
        Return a possible target for the probe to farm (own or unoccupied tile)
        """
        # first look next to the probe itself
        target = self._get_probe_farm_target(probe.coord)
        if target is not None:
            return target

        # then look next to the factories
        factories = self.factories.copy()
        dists = [np.linalg.norm(probe.coord - factory.coord) for factory in factories]
        while len(factories) > 0:
            i = np.argmin(dists)
            dists.pop(i)
            factory = factories.pop(i)

            target = self._get_probe_farm_target(factory.coord)
            if target is not None:
                return target

        # if nothing works: return the probe's coord -> wait
        return probe.coord

    def get_probe_attack_target(self, probe: Probe) -> Coord:
        """
        Return a possible target for the probe to attack
        """
        tiles: list[Tile] = []
        for player in self.game.players.values():
            if player is self:
                continue
            tiles += player.tiles

        if len(tiles) == 0:  # no tile to attack
            return probe.coord

        coords = np.array([tile.coord for tile in tiles])

        # get closest opponent tile
        dists = np.linalg.norm(coords - probe.pos, axis=1)
        idx = np.argmin(dists)
        tile = tiles[idx]

        # choose one of the tiles in region
        tiles = self.map.get_neighbour_tiles(tile, 3) + [tile]
        random.shuffle(tiles)
        for tile in tiles:
            if not tile.owner in (None, self):
                return tile.coord

    def _get_factory_income(self, factory: Factory) -> float:
        """
        Return the expenses of the `factory` (owned by the player)
        """
        return factory.get_income()

    def _get_tile_income(self, tile: Tile) -> float:
        """
        Return the income generated by the `tile` (owned by the player)
        """
        return tile.get_income()

    def _deprecate_tile(self, tile: Tile) -> TileStateModel | None:
        """
        If the `tile` meets the conditions,
        decrease its occupation with a certain probability.
        In case of decrease, return the `tile` state, else None
        """
        if tile.occupation <= 5:
            return None

        # compute probability
        prob = (tile.occupation - 5) / (self.config.max_occupation - 5)
        prob *= self.config.deprecate_rate

        if random.random() <= prob:
            tile.occupation -= 1
            return tile.get_state()
        return None

    def get_income(self) -> float:
        """
        Compute the income of the player
        """
        income = self.config.base_income
        for factory in self.factories:
            income += self._get_factory_income(factory)
        for tile in self.tiles:
            income += self._get_tile_income(tile)
        return income

    async def job_income(self):
        """
        Collect income, deprecate tiles
        """
        # create a unique id for the job
        jid = uuid.uuid4().hex
        # register job
        self._active_jobs.add(jid)

        while True:
            await JobManager.sleep(1)

            # stop condition
            if not jid in self._active_jobs:
                return

            # update player's money
            self.money = max(0, self.money + self.get_income())

            # deprecate tiles
            tiles = []
            for tile in self.tiles:
                state = self._deprecate_tile(tile)
                if state is not None:
                    tiles.append(state)

            yield GameStateModel(
                map=MapStateModel(tiles=tiles),
                players=[
                    PlayerStateModel(username=self.user.username, money=self.money)
                ],
            )

    @property
    def model(self) -> PlayerModel:
        """
        Return the model (pydantic) representation of the instance
        """
        return PlayerModel(
            username=self.user.username,
            money=self.money,
            score=self.score,
            alive=self.alive,
            factories=[factory.model for factory in self.factories],
            turrets=[turret.model for turret in self.turrets],
            probes=[probe.model for probe in self.probes],
        )
