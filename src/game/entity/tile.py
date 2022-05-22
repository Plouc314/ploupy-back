from __future__ import annotations
import numpy as np
from pydantic import BaseModel
from typing import TYPE_CHECKING

from src.core import PointModel, Coord

from .entity import Entity
from .factory import Factory
from .models import TileModel

if TYPE_CHECKING:
    from src.game.player import Player
    from src.game.models import GameConfig


class Tile(Entity):
    """
    Tile
    Occupation: score of how strongly the tile is occupied by the current owner
    """

    def __init__(self, coord: Coord, config: "GameConfig"):
        super().__init__(coord)
        self.config = config
        self.building: Factory | None = None
        self.owner: Player | None = None
        self.occupation: int = 0

    @property
    def occupied(self) -> bool:
        """
        Return if the tile is occupied by an player
        """
        return self.owner is not None and self.occupation > 0

    def claim(self, player: Player) -> bool:
        """
        Claim the tile for a player,
        lower the occupation if occupied by another player,
        else increment it.

        Return if the tile is occupied by the given player
        """
        if self.owner is None:
            self.owner = player
            self.occupation = 1
            return True

        if self.owner is player:
            self.occupation = min(self.occupation + 1, self.config.max_occupation)
            return True

        self.occupation -= 1
        if self.occupation == 0:
            self.owner = None

        return False

    def can_build(self, player: Player) -> bool:
        """
        Return if the given player can build a structure on the tile
        """
        return (
            self.building is None
            # and self.owner is player
            and self.occupation >= self.config.building_occupation_min
        )

    @property
    def model(self) -> TileModel:
        return TileModel(
            coord=PointModel.from_list(self._pos),
            owner=None if self.owner is None else self.owner.user.username,
            occupation=self.occupation,
        )
