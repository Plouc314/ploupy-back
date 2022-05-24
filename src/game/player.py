import random

from src.core import UserModel, PointModel, Coord

from src.game.entity.factory import Factory
from src.game.entity.probe import Probe
from src.game.entity.tile import Tile

from .exceptions import ActionException
from .models import GameConfig, PlayerModel
from .map import Map
from .geometry import Geometry

class Player:
    def __init__(self, user: UserModel, map: Map, config: GameConfig):
        self.user = user
        self.map = map
        self.config = config
        self.money = self.config.initial_money
        self.score = 0
        self.factories: list[Factory] = []
        self.probes: list[Probe] = []
        
        # dict between tile & probes going to the tile
        self._tiles: dict[Tile, Probe] = {}

    def build_factory(self, coord: PointModel) -> Factory:
        """
        Build a factory at the given coord is possible
        """
        if self.money < self.config.factory_price:
            raise ActionException(f"Not enough money ({self.money})")

        self.money -= self.config.factory_price

        factory = Factory(self, coord.coord)
        self.factories.append(factory)
        return factory

    def build_probe(self, pos: PointModel) -> Probe:
        '''
        Build a probe at the given position (no check on position)
        '''
        probe = Probe(self, pos.pos)
        self.probes.append(probe)
        return probe

    def add_tile(self, tile: Tile) -> None:
        '''
        Add a tile to the player

        NOTE: should only be called inside `Tile.claim` to keep the player & tile
        synchronized.
        '''
        if not tile in self._tiles.keys():
            self._tiles[tile] = []
    
    def remove_tile(self, tile: Tile) -> None:
        '''
        Remove a tile from the player

        NOTE: should only be called inside `Tile.claim` to keep the player & tile
        synchronized.
        '''
        if tile in self._tiles.keys():
            self._tiles.pop(tile)

    def get_probe_target(self, probe: Probe) -> Coord:
        '''
        Select the probe target (own or unoccupied tile)
        '''
        poss = list(Geometry.square(probe.coord, 3))
        poss.remove(tuple(probe.coord))
        random.shuffle(poss)

        for coord in poss:
            tile = self.map.get_tile(*coord)
            if tile is None:
                continue
            
            # check if tile occupied by an other player
            if tile.occupation > 0 and tile.owner is not self:
                continue

            # check if tile occupation full
            probes = self._tiles.get(tile, [])
            if tile.occupation + len(probes) >= self.config.max_occupation:
                continue

            # check if tile is isolated
            if tile.occupation == 0:
                neighbours = self.map.get_neighbour_tiles(tile)
                for neighbour in neighbours:
                    if neighbour.owner is self:
                        break
                else:
                    continue

            return coord

        print("no coord")
        return poss[0]

    @property
    def model(self) -> PlayerModel:
        """
        Return the model (pydantic) representation of the instance
        """
        return PlayerModel(
            username=self.user.username,
            money=self.money,
            score=self.score,
            factories=[factory.model for factory in self.factories],
            probes=[probe.model for probe in self.probes],
        )
