from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

from src.core import PointModel, Coord

from .entity import Entity
from .factory import Factory
from .turret import Turret
from .models import TileModel, TileStateModel

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
        self.building: Factory | Turret | None = None
        self._owner: Player | None = None
        self.occupation: int = 0

    @property
    def owner(self) -> Player | None:
        return self._owner

    @property
    def occupied(self) -> bool:
        """
        Return if the tile is occupied by an player
        """
        return self._owner is not None and self.occupation > 0

    def claim(self, player: Player) -> bool:
        """
        Claim the tile for a player

        Lower the occupation if occupied by another player,
        else increment it.

        Return if the tile is occupied by the given player
        """
        # tile is unoccupied
        if self._owner is None:
            self._owner = player
            self._owner.add_tile(self)
            self.occupation = 1
            return True

        # tile is occupied by same player
        if self._owner is player:
            self.occupation = min(self.occupation + 1, self.config.max_occupation)
            return True

        # tile is occupied by other player
        self.occupation -= 1
        if self.occupation == 0:
            self._owner.remove_tile(self)

            # in case a building was on the tile -> remove it
            if self.building is not None:
                self.building.die()
                self.building = None

            self._owner = None

        return False

    def can_build(self, player: Player) -> bool:
        """
        Return if the given player can build a structure on the tile
        """
        return (
            self.building is None
            and self._owner is player
            and self.occupation >= self.config.factory_occupation_min
        )

    def get_income(self) -> float:
        """
        Compute the income of the tile
        """
        return self.occupation * self.config.income_rate

    def get_state(self) -> TileStateModel:
        """
        Return the tile state (occupation and owner)
        """
        return TileStateModel(
            id=self.id,
            owner=None if self._owner is None else self._owner.user.username,
            occupation=self.occupation,
        )

    @property
    def model(self) -> TileModel:
        return TileModel(
            id=self.id,
            coord=PointModel.from_list(self._pos),
            owner=None if self._owner is None else self._owner.user.username,
            occupation=self.occupation,
        )
