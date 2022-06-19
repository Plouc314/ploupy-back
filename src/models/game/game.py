from pydantic import BaseModel

from src.models.core import core
import src.models.game.entities as entities



class Map(BaseModel):
    tiles: list[entities.Tile]


class MapState(BaseModel):
    tiles: list[entities.TileState] = []


class Player(BaseModel):
    username: str
    money: int
    score: int
    alive: bool
    income: int
    factories: list[entities.Factory]
    turrets: list[entities.TurretState]
    probes: list[entities.Probe]


class PlayerState(BaseModel):
    username: str
    money: int | None = None
    score: int | None = None
    alive: bool | None = None
    income: int | None = None
    factories: list[entities.FactoryState] = []
    turrets: list[entities.TurretState] = []
    probes: list[entities.ProbeState] = []


class Game(BaseModel):
    config: core.GameConfig
    map: Map
    players: list[Player]


class GameState(BaseModel):
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
    ranking: list[core.User]
    """players: from best (idx: 0) to worst (idx: -1)"""
    stats: list[GamePlayerStats]


class BuildFactoryResponse(BaseModel):
    username: str
    money: int
    factory: entities.Factory


class BuildTurretResponse(BaseModel):
    username: str
    money: int
    turret: entities.Turret


class BuildProbeResponse(BaseModel):
    username: str
    money: int
    probe: entities.Probe


class TurretFireProbeResponse(BaseModel):
    username: str
    turret_id: str
    probe: entities.ProbeState
