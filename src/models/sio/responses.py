from src.models.core import core
from src.models.game import game

from .sio import QueueState as _QueueState


class QueueStates(core.Response):
    """
    Represents the states of some queues
    """

    queues: list[_QueueState]


class GameResults(core.Response):
    """
    Represents the results of a game
    Including the statistics of the game
    and the mmrs updates.
    """

    ranking: list[core.User]
    """players: from best (idx: 0) to worst (idx: -1)"""
    stats: list[game.GamePlayerStats]
    """
    in-game statistics of each player (same order as ranking)
    """
    mmrs: list[int]
    """
    new mmr of players in game 
    """
    mmr_diffs: list[int]
    """
    mmr difference of players in game (same order as ranking)
    """
