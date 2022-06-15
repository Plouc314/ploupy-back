from src.core import GameModeModel, GeneralStatsModel


def get_mmr_diff(genstats: GeneralStatsModel, mode: GameModeModel, ranking: int) -> int:
    """
    Compute the mmr difference

    Args:
        - genstats: Stats to update (note: `scores` won't be updated)
        - mode: Game mode of the game
        - ranking: The rank position in the game (best: 0)
    """
    # get number of game played
    n_games = sum(genstats.scores)

    # normalize rank between [0, 1]
    normalized_ranking = ranking / (mode.config.n_player - 1)
    # performance between [1, -1]
    perf = 1 - 2 * normalized_ranking

    return 10 * perf