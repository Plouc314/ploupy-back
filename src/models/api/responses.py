"""
Represents responses of the rest API
Each class matches an endpoint of the API
"""

from src.models.core import core as _c


class UserData(_c.Response):
    user: _c.User
    mmrs: _c.UserMMRs


class CreateUser(_c.Response):
    pass


class UserOnline(_c.Response):
    pass


class GameMode(_c.Response):
    game_modes: list[_c.GameMode]


class GameResults(_c.Response):
    mmrs: list[int]
    """
    new mmr of players in game (same order as ranking)
    """
    mmr_diffs: list[int]
    """
    mmr difference of players in game (same order as ranking)
    """


class UserStats(_c.Response):
    stats: list[_c.ExtendedGameModeStats]
