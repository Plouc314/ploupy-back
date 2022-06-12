from src.core import ResponseModel, UserModel, GameConfig


class UserResponse(ResponseModel):
    user: UserModel


class GameConfigResponse(ResponseModel):
    game_config: GameConfig
