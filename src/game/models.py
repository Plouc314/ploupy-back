from pydantic import BaseModel

from src.core import PointModel

from src.game.entity.models import (
    TileModel,
    TileStateModel,
    FactoryModel,
    FactoryStateModel,
    ProbeModel,
    ProbeStateModel,
)


class MapModel(BaseModel):
    tiles: list[TileModel]


class MapStateModel(BaseModel):
    tiles: list[TileStateModel] = []


class PlayerModel(BaseModel):
    username: str
    money: int
    score: int
    factories: list[FactoryModel]
    probes: list[ProbeModel]


class PlayerStateModel(BaseModel):
    username: str
    money: int | None = None
    score: int | None = None
    factories: list[FactoryStateModel] = []
    probes: list[ProbeStateModel] = []


class GameConfig(BaseModel):
    dim: PointModel
    initial_money: int
    factory_price: int
    building_occupation_min: int
    """minimal occupation value on tile required on target tile"""
    max_occupation: int
    """maximal occupation value that can be reached"""


class GameModel(BaseModel):
    config: GameConfig
    map: MapModel
    players: list[PlayerModel]


class GameStateModel(BaseModel):
    map: MapStateModel | None = None
    players: list[PlayerStateModel] = []
