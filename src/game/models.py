from pydantic import BaseModel

from src.core import GameConfig, UserModel

from src.game.entity.models import (
    TileModel,
    TileStateModel,
    FactoryModel,
    FactoryStateModel,
    ProbeModel,
    ProbeStateModel,
    TurretModel,
    TurretStateModel,
)


class MapModel(BaseModel):
    tiles: list[TileModel]


class MapStateModel(BaseModel):
    tiles: list[TileStateModel] = []


class PlayerModel(BaseModel):
    username: str
    money: int
    score: int
    alive: bool
    income: int
    factories: list[FactoryModel]
    turrets: list[TurretStateModel]
    probes: list[ProbeModel]


class PlayerStateModel(BaseModel):
    username: str
    money: int | None = None
    score: int | None = None
    alive: bool | None = None
    income: int | None = None
    factories: list[FactoryStateModel] = []
    turrets: list[TurretStateModel] = []
    probes: list[ProbeStateModel] = []


class GameModel(BaseModel):
    config: GameConfig
    map: MapModel
    players: list[PlayerModel]


class GameStateModel(BaseModel):
    map: MapStateModel | None = None
    players: list[PlayerStateModel] = []


class GamePlayerStatsModel(BaseModel):
    username: str
    money: list[int]
    occupation: list[int]
    factories: list[int]
    turrets: list[int]
    probes: list[int]


class GameResultResponse(BaseModel):
    ranking: list[UserModel]
    """players: from best to worst"""
    stats: list[GamePlayerStatsModel]


class BuildFactoryResponse(BaseModel):
    username: str
    money: int
    factory: FactoryModel


class BuildTurretResponse(BaseModel):
    username: str
    money: int
    turret: TurretModel


class BuildProbeResponse(BaseModel):
    username: str
    money: int
    probe: ProbeModel


class TurretFireProbeResponse(BaseModel):
    username: str
    turret_id: str
    probe: ProbeStateModel
