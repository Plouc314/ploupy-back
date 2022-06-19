"""
Represents responses of the rest API
Each class matches an endpoint of the API
"""

from src.models.core import core


class UserData(core.Response):
    user: core.User


class CreateUser(core.Response):
    pass


class GameMode(core.Response):
    game_modes: list[core.GameMode]


class GameResults(core.Response):
    mmrs: list[int]
    """
    new mmr of players in game (same order as ranking)
    """
    mmr_diffs: list[int]
    """
    mmr difference of players in game (same order as ranking)
    """


class UserStats(core.Response):
    stats: list[core.GameModeStats]
