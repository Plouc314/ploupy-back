from src.core import ResponseModel
from src.game.entity import FactoryModel


class ActionBuildResponse(ResponseModel):
    username: str
    factory: FactoryModel
