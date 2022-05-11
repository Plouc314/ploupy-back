import numpy as np

from src.core import User

from .models import (
    GameConfig,
    GameStateServer,
    PlayerStateClient,
    PlayerStateServer,
    Point2D,
    Pos,
)
from .map import Map
from .player import Player


class Game:
    def __init__(self, users: list[User], config: GameConfig):
        self.users = {u.username: u for u in users}
        self.config = config
        self.map = Map(config.dim.coord)
        self.players = self._build_players()

    def _build_players(self) -> dict[str, Player]:
        """
        Build and return players
        """
        players = {}
        positions = self._get_start_positions(len(self.users))

        for user, pos in zip(self.users.values(), positions):
            player = Player(user, pos)
            players[user.username] = player

        return players

    def _get_start_positions(self, n: int) -> list[Pos]:
        """
        Return suitable start positions for n players
        """
        positions = []
        for i in range(n):
            pos = np.random.randint(0, np.min(self.map.dim), 2)
            positions.append(pos)
        return positions

    def update_player_state(
        self, username: str, state: PlayerStateClient
    ) -> PlayerStateServer:
        """ """
        player = self.players[username]
        player.pos = state.position.pos

        # floor position to get coordinate
        coord = [int(state.position.x), int(state.position.y)]

        tiles = []
        tile = self.map.get_tile(*coord)
        if tile is not None:
            tiles = [Point2D.from_list(tile.coord)]
            if tile.owner:
                tile.owner.remove_tile(tile)
            player.add_tile(tile)

        return PlayerStateServer(
            username=username, position=state.position, score=player.score, tiles=tiles
        )

    def get_game_state(self) -> GameStateServer:
        """
        Return the current game state
        """
        return GameStateServer(
            dim=Point2D.from_list(self.map.dim),
            players=[
                PlayerStateServer(
                    username=player.user.username,
                    position=Point2D.from_list(player.pos),
                    score=player.score,
                    tiles=[Point2D.from_list(tile.coord) for tile in player.tiles],
                )
                for player in self.players.values()
            ],
        )
