import numpy as np

from src.core import User

from .models import GameConfig, PlayerStateClient, PlayerStateServer, Pos
from .map import Map
from .player import Player

class Game:
    
    def __init__(self, users: list[User], config: GameConfig):
        self.users = {u.username: u for u in users}
        self.config = config
        self.map = Map(config.dim.coord)
        self.players = self._build_players()

    def _build_players(self) -> dict[str, Player]:
        '''
        Build and return players
        '''
        players = {}
        positions = self._get_start_positions(len(self.users))
        
        for user, pos in zip(self.users.values(), positions):
            player = Player(user, pos)
            players[user.username] = player
        
        return players

    def _get_start_positions(self, n: int) -> list[Pos]:
        '''
        Return suitable start positions for n players
        '''
        positions = []
        for i in range(n):
            pos = np.random.randint(0, np.min(self.map.dim), 2)
            positions.append(pos)
        return positions
    
    def on_player_update(self, state: PlayerStateClient) -> PlayerStateServer:
        '''
        '''
        player = self.players[state.username]
        player.pos = state.position.pos

        tiles = []
        tile = self.map.get_tile(state.position.x, state.position.y)
        if tile is not None:
            tiles = [tile]
            if tile.owner:
                tile.owner.remove_tile(tile)
            player.add_tile(tile)
        

        return PlayerStateServer(
            username=state.username,
            position=state.position,
            tiles=tiles
        )