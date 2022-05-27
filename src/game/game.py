import numpy as np


from src.core import UserModel, PointModel, Coord
from src.sio import JobManager
from src.game.entity.models import FactoryModel, ProbeStateModel

from .geometry import Geometry
from .map import Map
from .player import Player
from .exceptions import ActionException
from .models import (
    BuildFactoryResponse,
    GameModel,
    GameConfig,
    GameStateModel,
    MapStateModel,
    PlayerStateModel,
)


class Game:
    def __init__(
        self, users: list[UserModel], job_manager: JobManager, config: GameConfig
    ):
        self.users = {u.username: u for u in users}
        self.job_manager = job_manager
        self.config = config
        self.map = Map(config)
        self.players: dict[str, Player] = {}

        self._build_players()

    def _build_players(self) -> list[Player]:
        """
        Build players and their start positions

        Start income job
        """
        self.players = {}
        positions = self._get_start_positions(len(self.users))

        for user, pos in zip(self.users.values(), positions):
            player = Player(user, self.map, self.job_manager, self.config)
            self.players[user.username] = player
            self._build_initial_territory(player, pos)

            job = self.job_manager.make_job("game_state", player.job_income)
            job.start()

        return self.players

    def _get_start_positions(self, n: int) -> list[Coord]:
        """
        Return suitable start positions for n players
        """
        radius = np.min(self.map.dim) // 2
        margin = radius // 5
        positions = []
        for i in range(n):
            angle = i / n * 2 * np.pi
            pos = np.array([np.sin(angle), np.cos(angle)])
            pos = (radius - margin) * pos + radius
            positions.append(pos.astype(int))
        return positions

    def _build_initial_territory(self, player: Player, origin: Coord):
        """ """
        coords = Geometry.square(origin, 3)
        for coord in coords:
            tile = self.map.get_tile(coord[0], coord[1])
            if tile is None:
                continue
            for i in range(5):
                tile.claim(player)

        # build an initial factory
        player.money += self.config.factory_price
        player.build_factory(PointModel.from_list(origin))

    def action_build_factory(
        self, player: Player, coord: PointModel
    ) -> BuildFactoryResponse:
        """
        Build a factory at the given coord for the given player is possible

        Raise: ActionException
        """
        tile = self.map.get_tile(*coord.coord)
        if tile is None:
            raise ActionException(f"Tile coordinate is invalid ({coord.coord})")

        if not tile.can_build(player):
            raise ActionException("Cannot build on tile")

        factory = player.build_factory(coord)

        tile.building = factory

        job_expand = self.job_manager.make_job("game_state", factory.job_expand)
        job_expand.start(self.map)

        job_probe = self.job_manager.make_job("build_probe", factory.job_probe)
        job_probe.start(self.map)

        return BuildFactoryResponse(
            username=player.user.username, money=player.money, factory=factory.model
        )

    def action_move_probes(
        self, player: Player, ids: list[str], targets: list[PointModel]
    ) -> GameStateModel:
        """
        Change the target of the probes with the given `ids`

        Raise: ActionException
        """
        if len(ids) != len(targets):
            raise ActionException(
                f"There should be the same number of ids and targets ({len(ids)} != {len(targets)})."
            )

        states = []

        for id, target in zip(ids, targets):
            probe = player.get_probe(id)
            if probe is None:
                continue

            # assert that the target is valid
            tile = self.map.get_tile(*target.coord)
            if tile is None:
                continue

            # stop current movement job
            probe.stop_jobs()

            # set new target
            probe.set_target(target.coord)

            # start new movement job
            job_move = self.job_manager.make_job("game_state", probe.job_move)
            job_move.start(self.map)

            states.append(probe.get_state())

        return GameStateModel(
            players=[PlayerStateModel(username=player.user.username, probes=states)]
        )

    def action_explode_probes(self, player: Player, ids: list[str]) -> GameStateModel:
        """
        Explode the probes with the given `ids`
        """
        probes = []
        tiles = []

        for id in ids:
            probe = player.get_probe(id)
            if probe is None:
                continue

            tiles += player.explode_probe(probe)
            probes.append(ProbeStateModel(id=probe.id, alive=probe.alive))

        return GameStateModel(
            map=MapStateModel(tiles=tiles),
            players=[PlayerStateModel(username=player.user.username, probes=probes)],
        )

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
