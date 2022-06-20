from src.models import core as _c, game as _g

import src.models.sio.sio as _s


class UserManagerState(_c.Response):
    """
    Represents the state of the user manager

    Contains currently connected users
    """

    users: list[_s.UserState]


class QueueManagerState(_c.Response):
    """
    Represents the state of the queue manager
    """

    queues: list[_s.QueueState]


class GameManagerState(_c.Response):
    """
    Represents the state of the game manager

    Contains currently played games
    """

    games: list[_s.GameState]


class GameResults(_c.Response):
    """
    Represents the results of a game
    Including the statistics of the game
    and the mmrs updates.
    """

    ranking: list[_c.User]
    """players: from best (idx: 0) to worst (idx: -1)"""
    stats: list[_g.GamePlayerStats]
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
