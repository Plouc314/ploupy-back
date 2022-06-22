from src.models import core

def get_mmr_diff(mode: core.GameMode, ranking: int) -> int:
    """
    Compute the mmr difference

    Args:
        - mode: Game mode of the game
        - ranking: The rank position in the game (best: 0)
    """
    # normalize rank between [0, 1]
    normalized_ranking = ranking / (mode.config.n_player - 1)
    # performance between [1, -1]
    perf = 1 - 2 * normalized_ranking

    return 10 * perf