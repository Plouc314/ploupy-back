import numpy as np
from pydantic import BaseModel

from src.core import UserModel, PointModel, Pos
from src.game.entity import FactoryModel

from .map import Map
from .player import Player, PlayerModel
from .exceptions import ActionException


class GameConfig(BaseModel):
    dim: PointModel
    initial_money: int
    factory_price: int


class GameModel(BaseModel):
    config: GameConfig
    players: list[PlayerModel]


class Game:
    def __init__(self, users: list[UserModel], config: GameConfig):
        self.users = {u.username: u for u in users}
        self.config = config
        self.map = Map(config.dim.coord)
        self.players: dict[str, Player] = {}

        self._build_players()

    def _build_players(self) -> None:
        """
        Build players
        """
        self.players = {}
        positions = self._get_start_positions(len(self.users))

        for user, pos in zip(self.users.values(), positions):
            player = Player(user, pos, self.config.initial_money)
            self.players[user.username] = player

        return self.players

    def _get_start_positions(self, n: int) -> list[Pos]:
        """
        Return suitable start positions for n players
        """
        positions = []
        for i in range(n):
            pos = np.random.randint(0, np.min(self.map.dim), 2)
            positions.append(pos)
        return positions

    def build_factory(self, player: Player, coord: PointModel) -> FactoryModel:
        """
        Build a factory at the given coord for the given player is possible
        """
        tile = self.map.get_tile(*coord.coord)
        if tile is None:
            raise ActionException(f"Tile coordinate is invalid ({coord.coord})")

        if tile.building is not None:
            raise ActionException("Tile is taken")

        factory = player.build_factory(coord, self.config.factory_price)

        tile.building = factory

        return factory.model

    def get_player(self, username: str) -> Player | None:
        """
        Return the player with the given username
        """
        return self.players.get(username, None)

    @property
    def model(self) -> GameModel:
        """
        Return the model (pydantic) representation of the instance
        """
        return GameModel(
            config=self.config, players=[player.model for player in self.players.values()]
        )
