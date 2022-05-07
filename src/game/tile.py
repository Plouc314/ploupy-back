from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING

from .models import Coord

if TYPE_CHECKING:
    from .player import Player

class Tile:

    def __init__(self, coord: Coord, owner: "Player" | None = None):
        self.coord = np.array(coord, dtype=int)
        self.owner = owner
