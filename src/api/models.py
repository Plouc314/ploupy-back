from pydantic import BaseModel

from src.core import ResponseModel, UserModel, GameModeModel, GameConfig, GameModes


class GameResultsAPI(BaseModel):

    gmid: str
    """
    Game mode id of mode in which the game was played
    """
    ranking: list[str]
    """
    list of the `uid` of the users,
    from best (index: 0) to worst
    """


class UserResponse(ResponseModel):
    user: UserModel


class GameModeResponse(ResponseModel):
    game_mode: GameModeModel


class GameResultsAPIResponse(ResponseModel):
    mmrs: list[int]
    """
    new mmr of players in game (same order as ranking)
    """
    mmr_diffs: list[int]
    """
    mmr difference of players in game (same order as ranking)
    """


class AllGameModeResponse(ResponseModel):
    game_modes: list[GameModeModel]


class GameConfigResponse(ResponseModel):
    game_config: GameConfig
