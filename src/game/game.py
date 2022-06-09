from typing import Callable
import numpy as np


from src.core import UserModel, PointModel, Coord
from src.sio import JobManager
from src.game.entity.models import FactoryModel, ProbePolicy, ProbeStateModel

from .map import Map
from .player import Player
from .exceptions import ActionException
from .models import (
    BuildFactoryResponse,
    BuildTurretResponse,
    GameModel,
    GameConfig,
    GameResultResponse,
    GameStateModel,
    MapStateModel,
    PlayerStateModel,
)


class Game:
    def __init__(
        self,
        users: list[UserModel],
        job_manager: JobManager,
        config: GameConfig,
        on_end_game: Callable[["Game"], None],
    ):
        self.users = {u.username: u for u in users}
        self.job_manager = job_manager
        self.config = config
        self.map = Map(config)
        self.players: dict[str, Player] = {}

        # if the game is finished
        self.ended = False

        # function called when the game ends
        self._on_end_game = on_end_game

        self._dead_players: list[Player] = []

        self._build_players()

    def _build_players(self) -> list[Player]:
        """
        Build players and their start positions

        Start income job
        """
        self.players = {}
        positions = self._get_start_positions(len(self.users))

        for user, pos in zip(self.users.values(), positions):
            player = Player(user, self)
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
        tile = self.map.get_tile(origin[0], origin[1])
        if tile is None:
            raise Exception("Starting position is invalid")

        for i in range(self.config.building_occupation_min):
            tile.claim(player)

        # build an initial factory
        player.money += self.config.factory_price
        self.action_build_factory(player, PointModel.from_list(origin))

        # build initial probes
        factory = player.factories[0]
        player.money += self.config.initial_n_probes * self.config.probe_price
        for i in range(self.config.initial_n_probes):
            factory.build_probe(self.map, self.job_manager)

    def end_game(self, notify_client: bool = True, delay: float = 0.5):
        """
        End the game (Will only be done once)

        Call `_on_end_game`

        If `notify_client` is true, notify client of the game result
        (wait for `delay` before sending the response)
        """
        if self.ended:
            return
        self.ended = True

        winners: list[Player] = []

        for player in self.players.values():
            if player.alive:
                # kill remaining players
                player.die(notify_client=notify_client, is_winner=True)
                winners.append(player)

        ranking = winners + self._dead_players[::-1]

        if notify_client:
            self.job_manager.send(
                "game_result",
                GameResultResponse(ranking=[player.user for player in ranking]),
                delay=delay,
                on_send=lambda: self._on_end_game(self),
            )
        else:
            # still call on-end-game callback
            self._on_end_game(self)

    def get_player(self, username: str) -> Player | None:
        """
        Return the player with the given username
        """
        return self.players.get(username, None)

    def notify_death(self, player: Player):
        """
        Notify `self` of the death of a player.
        If all but one players are dead, end the game.

        Notify client of the game result
        """
        if self.ended:
            return
        if not player in self._dead_players:
            self._dead_players.append(player)

        if len(self._dead_players) == self.config.n_player - 1:
            self.end_game()

    def action_resign_game(self, player: Player) -> None:
        """
        Make one player die
        """
        player.die()

    def action_build_factory(
        self, player: Player, coord: PointModel
    ) -> BuildFactoryResponse:
        """
        Build a factory at the given coord for the given player is possible

        Raise: ActionException
        """
        if not player.alive:
            raise ActionException("You are dead ?!")

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
            username=player.username, money=player.money, factory=factory.model
        )

    def action_build_turret(
        self, player: Player, coord: PointModel
    ) -> BuildTurretResponse:
        """
        Build a turret at the given coord for the given player is possible

        Raise: ActionException
        """
        if not player.alive:
            raise ActionException("You are dead ?!")

        tile = self.map.get_tile(*coord.coord)
        if tile is None:
            raise ActionException(f"Tile coordinate is invalid ({coord.coord})")

        if not tile.can_build(player):
            raise ActionException("Cannot build on tile")

        turret = player.build_turret(coord)

        tile.building = turret

        job_fire = self.job_manager.make_job("turret_fire_probe", turret.job_fire)
        job_fire.start()

        return BuildTurretResponse(
            username=player.username, money=player.money, turret=turret.model
        )

    def action_move_probes(
        self, player: Player, ids: list[str], targets: list[PointModel]
    ) -> GameStateModel:
        """
        Change the target of the probes with the given `ids`

        Raise: ActionException
        """
        if not player.alive:
            raise ActionException("You are dead ?!")

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

            # can't move on opponent tile
            if not tile.owner in (None, player):
                continue

            # stop current movement job
            probe.stop()

            # set new target
            probe.set_target(target.coord)

            # start new movement job
            job_move = self.job_manager.make_job("game_state", probe.job_move)
            job_move.start(self.map)

            states.append(probe.get_state())

        if len(states) == 0 and len(targets) > 0:
            raise ActionException("Invalid targets.")

        return GameStateModel(
            players=[PlayerStateModel(username=player.username, probes=states)]
        )

    def action_explode_probes(self, player: Player, ids: list[str]) -> GameStateModel:
        """
        Explode the probes with the given `ids`
        """
        if not player.alive:
            raise ActionException("You are dead ?!")

        probes = []
        tiles = []

        for id in ids:
            probe = player.get_probe(id)
            if probe is None:
                continue

            tiles += probe.explode(self.map)
            probes.append(ProbeStateModel(id=probe.id, alive=probe.alive))

        return GameStateModel(
            map=MapStateModel(tiles=[tile.get_state() for tile in tiles]),
            players=[PlayerStateModel(username=player.username, probes=probes)],
        )

    def action_probes_attack(self, player: Player, ids: list[str]) -> GameStateModel:
        """
        Make the probes with the given `ids` attack the opponents
        """
        if not player.alive:
            raise ActionException("You are dead ?!")

        states = []

        for id in ids:
            probe = player.get_probe(id)
            if probe is None:
                continue

            # select a target
            target = player.get_probe_attack_target(probe)

            # stop current movement job (and potential attack)
            probe.stop()

            # set probe policy to attack
            probe.set_policy(ProbePolicy.ATTACK)

            # set new target
            probe.set_target(target)

            # start new movement job
            job_move = self.job_manager.make_job("game_state", probe.job_move)
            job_move.start(self.map)

            states.append(probe.get_state())

        return GameStateModel(
            players=[PlayerStateModel(username=player.username, probes=states)]
        )

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
