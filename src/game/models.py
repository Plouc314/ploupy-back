from pydantic import BaseModel

from src.core import PointModel, UserModel

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
    factories: list[FactoryModel]
    turrets: list[TurretStateModel]
    probes: list[ProbeModel]


class PlayerStateModel(BaseModel):
    username: str
    money: int | None = None
    score: int | None = None
    alive: bool | None = None
    factories: list[FactoryStateModel] = []
    turrets: list[TurretStateModel] = []
    probes: list[ProbeStateModel] = []


class GameConfig(BaseModel):
    dim: PointModel
    """
    dimension of the map (unit: coord)
    """
    n_player: int
    """
    number of players in the game
    """
    initial_money: int
    """
    money players start with
    """
    initial_n_probes: int
    """
    initial number of probes to start with (must be smaller
    than `factory_max_probe`)
    """
    base_income: float
    """
    base income that each player receive unconditionally
    """
    building_occupation_min: int
    """
    minimal occupation value on tile required to build a building (factory/turret)
    """
    factory_price: int
    """
    amount to pay to build a new factory
    """
    factory_max_probe: int
    """
    maximal number of probe generated by a factory
    """
    factory_build_probe_delay: float
    """
    delay to wait to build a probe from the factory (sec)
    """
    max_occupation: int
    """
    maximal occupation value that can be reached
    """
    probe_speed: float
    """
    speed of the probe in coordinate/sec
    """
    probe_price: int
    """
    amount to pay to produce one probe
    """
    probe_claim_delay: float
    """
    delay to wait claim a tile, the probe can be manually moved but not claim
    another tile during the delay (see Probe `is_claiming` flag for details)
    """
    probe_maintenance_costs: float
    """
    Costs of possessing one probe (computed in the player's income)
    """
    turret_price: int
    """
    amount to pay to build a new turret
    """
    turret_fire_delay: float
    """
    delay to wait for the turret between two fires (sec)
    """
    turret_scope: float
    """
    scope of the turret (unit: coord)
    """
    income_rate: float
    """
    factor of how the occupation level of a tile reflects on its income,
    as `income = occupation * rate`
    """
    deprecate_rate: float
    """
    probability that a tile with maximum occupation lose 1 occupation
    """


class GameModel(BaseModel):
    config: GameConfig
    map: MapModel
    players: list[PlayerModel]


class GameStateModel(BaseModel):
    map: MapStateModel | None = None
    players: list[PlayerStateModel] = []


class GameResultResponse(BaseModel):
    ranking: list[UserModel]
    '''players: from best to worst'''


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