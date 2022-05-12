import numpy as np

from src.core import User

from .tile import Tile
from .models import Pos

class Player:
    
    def __init__(self, user: User, pos: Pos):
        self.user = user
        self.pos = np.array(pos, dtype=float)
        self.score = 0
        self.tiles: list[Tile] = []
    
    def add_tile(self, tile: Tile) -> None:
        '''
        Add a tile to the user,
        if tile is new: update score
        '''
        if tile in self.tiles:
            return
        
        self.tiles.append(tile)
        self.score += 1
    
    def remove_tile(self, tile: Tile) -> None:
        '''
        Remove a tile of the user,
        if tile exists: update score
        '''
        if not tile in self.tiles:
            return
        
        self.tiles.remove(tile)
        self.score -= 1