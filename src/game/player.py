import numpy as np

from src.core import UserModel, PointModel

from src.game.entity.factory import Factory
from src.game.entity.probe import Probe

from .exceptions import ActionException
from .models import GameConfig, PlayerModel
from .map import Map

class Player:
    def __init__(self, user: UserModel, map: Map, config: GameConfig):
        self.user = user
        self.map = map
        self.config = config
        self.money = self.config.initial_money
        self.score = 0
        self.factories: list[Factory] = []
        self.probes: list[Probe] = []

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
        Build a probe at the given position is possible
        '''
        probe = Probe(self, pos.pos)
        self.probes.append(probe)
        return probe

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
