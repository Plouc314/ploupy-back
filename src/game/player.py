import numpy as np
from pydantic import BaseModel

from src.core import UserModel, PointModel, Pos
from src.game.entity import Factory, FactoryModel, Probe, ProbeModel

from .exceptions import ActionException

class PlayerModel(BaseModel):
    username: str
    money: int
    score: int
    factories: list[FactoryModel]
    probes: list[ProbeModel]


class Player:
    def __init__(self, user: UserModel, pos: Pos, money: int):
        self.user = user
        self.pos = np.array(pos, dtype=float)
        self.money = money
        self.score = 0
        self.factories: list[Factory] = []
        self.probes: list[Probe] = []

    def build_factory(self, coord: PointModel, price: int) -> Factory:
        '''
        Build a factory at the given coord is possible
        '''
        if self.money < price:
            raise ActionException(f"Not enough money ({self.money})")
        
        self.money -= price

        factory = Factory(self, coord.coord)
        self.factories.append(factory)
        return factory

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
