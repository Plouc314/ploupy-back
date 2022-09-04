import numpy as np
from datetime import datetime
from pydantic import BaseModel


Coord = list | tuple | np.ndarray
Pos = list | tuple | np.ndarray


class Point(BaseModel):
    """
    Represent a point in 2D
    """

    x: float
    y: float

    @classmethod
    def from_list(cls, point: Pos) -> "Point":
        """
        Build an instance of Point from a list
        """
        return Point(x=point[0], y=point[1])

    @property
    def coord(self) -> np.ndarray:
        """
        Return the point as coordinate (int dtype)
        """
        return np.array([self.x, self.y], dtype=int)

    @property
    def pos(self) -> np.ndarray:
        """
        Return the point as position (float dtype)
        """
        return np.array([self.x, self.y], dtype=float)


class Response(BaseModel):
    """
    Represent a response from a server (api/sio)
    """

    success: bool = True
    msg: str = ""


class GameConfig(BaseModel):
    """
    Global configuration of the game

    Merge with GameMetadata fields to get rust GameConfig.
    """

    initial_money: int
    initial_n_probes: int
    base_income: float
    building_occupation_min: int
    factory_price: int
    factory_expansion_size: int
    factory_maintenance_costs: float
    factory_max_probe: int
    factory_build_probe_delay: float
    max_occupation: int
    probe_speed: float
    probe_hp: int
    probe_price: int
    probe_claim_delay: float
    probe_claim_intensity: int
    probe_explosion_intensity: int
    probe_maintenance_costs: float
    turret_price: int
    turret_damage: int
    turret_fire_delay: float
    turret_scope: float
    turret_maintenance_costs: float
    income_rate: float
    deprecate_rate: float
    tech_probe_explosion_intensity_increase: int
    tech_probe_explosion_intensity_price: float
    tech_probe_claim_intensity_increase: int
    tech_probe_claim_intensity_price: float
    tech_probe_hp_increase: int
    tech_probe_hp_price: float
    tech_factory_build_delay_decrease: float
    tech_factory_build_delay_price: float
    tech_factory_probe_price_decrease: float
    tech_factory_probe_price_price: float
    tech_factory_max_probe_increase: int
    tech_factory_max_probe_price: float
    tech_turret_scope_increase: float
    tech_turret_scope_price: float
    tech_turret_fire_delay_decrease: float
    tech_turret_fire_delay_price: float
    tech_turret_maintenance_costs_decrease: float
    tech_turret_maintenance_costs_price: float


class User(BaseModel):
    """
    Represent a user general informations
    """

    uid: str
    username: str
    email: str
    avatar: str
    """
    Name of the avatar
    (see ploupy-front `textures.tsx` for possible values)
    """
    is_bot: bool
    owner: str | None
    """
    In case the user is a bot:
    store the uid of its owner
    """
    bots: list[str]
    """
    List of bots uid
    """
    joined_on: datetime
    last_online: datetime


class UserKeys(BaseModel):
    """
    Represent keys of a user
    """

    bot_key: str
    """
    Key to connect as a bot (require user to be a bot)
    """


class GameMode(BaseModel):
    """
    Represent a game mode
    """

    id: str
    name: str
    config: GameConfig


class GameMetadata(BaseModel):
    """
    Metadata related to the game
    """

    dim: Point
    n_player: int


class DBConfig(BaseModel):
    """
    Represent the config node of the db
    """

    modes: list[GameMode]


class GameStats(BaseModel):
    """
    Represents the statistics of one game
    """

    date: datetime

    mmr: int
    """
    MMR of the user AFTER the game
    """

    ranking: list[str]
    """
    List of UIDs of the player in the game (including self)
    sorted by resulting position, i.e. best (index 0) to worst
    """


class UserMMRs(BaseModel):
    """
    Represents the current MMRs of the user in all game modes
    """

    mmrs: dict[str, int]
    """
    Key: game mode id
    Value: current MMR
    """


class GameModeHistory(BaseModel):
    """
    Represents the history of all played games
    in a specific mode
    """

    mode: GameMode
    history: list[GameStats]


class UserStats(BaseModel):
    """
    Represents the statistics and ranking of a user
    in all the modes
    """

    mmrs: UserMMRs
    history: dict[str, GameModeHistory]
    """
    all the game mode's histories
    keys: game mode id
    """


class ExtendedGameModeStats(BaseModel):
    """
    Represents the statistics for a game mode
    once processed, with as much insights as possible
    """

    mode: GameMode
    """
    game mode
    """

    scores: list[int]
    """
    List of occurence of the resulting position,
    for ex the value at index 0 indicates the number
    of times the user finished in first position
    """

    dates: list[str]
    """
    List of all the dates where a game was played
    Format: ISO
    """

    mmr_hist: list[int]
    """
    List of all the values of the MMR over time
    (same order as `dates`)
    """
