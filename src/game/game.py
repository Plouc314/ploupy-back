import numpy as np


from src.core import UserModel, PointModel, Coord
from src.sio import JobManager
from src.game.entity.models import FactoryModel

from .geometry import expansion
from .map import Map
from .player import Player
from .exceptions import ActionException
from .models import GameModel, GameConfig


class Game:
    def __init__(self, users: list[UserModel], job_manager: JobManager, config: GameConfig):
        self.users = {u.username: u for u in users}
        self.job_manager = job_manager
        self.config = config
        self.map = Map(config)
        self.players: dict[str, Player] = {}

        self._build_players()

    def _build_players(self) -> list[Player]:
        """
        Build players and their start positions
        """
        self.players = {}
        positions = self._get_start_positions(len(self.users))

        for user, pos in zip(self.users.values(), positions):
            player = Player(user, self.config)
            self.players[user.username] = player
            self._build_initial_expansion(player, pos)

        return self.players

    def _get_start_positions(self, n: int) -> list[Coord]:
        """
        Return suitable start positions for n players
        """
        radius = np.min(self.map.dim) // 2
        margin = np.max([3, radius//5])
        positions = []
        for i in range(n):
            angle = i/n * 2*np.pi
            pos = np.array([np.sin(angle), np.cos(angle)])
            pos = (radius - margin) * pos + radius
            positions.append(pos.astype(int))
        return positions

    def _build_initial_expansion(self, player: Player, coord: Coord):
        '''
        '''
        coords = expansion(coord, 3)
        for coord in coords:
            tile = self.map.get_tile(coord[0], coord[1])
            if tile is None:
                continue
            for i in range(5):
                tile.claim(player)


    def build_factory(self, player: Player, coord: PointModel) -> FactoryModel:
        """
        Build a factory at the given coord for the given player is possible
        """
        tile = self.map.get_tile(*coord.coord)
        if tile is None:
            raise ActionException(f"Tile coordinate is invalid ({coord.coord})")

        if not tile.can_build(player):
            raise ActionException("Cannot build on tile")

        factory = player.build_factory(coord)

        tile.building = factory

        job = self.job_manager.make_job("game_state", factory.expand_job)
        job.start(self.map)

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
            config=self.config,
            map=self.map.model,
            players=[player.model for player in self.players.values()],
        )
