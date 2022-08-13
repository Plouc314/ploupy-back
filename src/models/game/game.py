from pydantic import BaseModel

from src.models.core import core as _c
import src.models.game.entities as entities


class MapState(BaseModel):
    tiles: list[entities.TileState] = []


class PlayerState(BaseModel):
    uid: str
    username: str
    money: int | None = None
    death: str | None = None
    income: int | None = None
    factories: list[entities.FactoryState] = []
    turrets: list[entities.TurretState] = []
    probes: list[entities.ProbeState] = []


class GameState(BaseModel):
    gid: str
    config: _c.GameConfig | None = None
    map: MapState | None = None
    players: list[PlayerState] = []


class GamePlayerStats(BaseModel):
    username: str
    money: list[int]
    occupation: list[int]
    factories: list[int]
    turrets: list[int]
    probes: list[int]


class GameResult(BaseModel):
    ranking: list[_c.User]
    """players: from best (idx: 0) to worst (idx: -1)"""
    stats: list[GamePlayerStats]
