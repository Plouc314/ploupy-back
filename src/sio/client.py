from pydantic import BaseModel
import requests

from src.core import ResponseModel, GameModeModel, FLAG_DEPLOY
from src.api import GameResultsAPI, GameResultsAPIResponse
from src.api import (
    UserResponse,
    AllGameModeResponse,
    GameModeResponse,
)


class Client:
    """Client to the main api"""

    URL_DEV = "http://127.0.0.1:5000/api/"
    URL_DEPLOY = "https://ploupy.herokuapp.com/api/"
    URL = URL_DEPLOY if FLAG_DEPLOY else URL_DEV

    def __init__(self):
        self._game_modes: dict[str, GameModeModel] = {}

        # load game modes
        modes = self.get_game_mode(all=True)
        for mode in modes:
            self._game_modes[mode.id] = mode

    def get(self, endpoint: str, args: dict) -> dict | None:
        """
        Send a GET requests to the api
        """
        url = f"{self.URL}{endpoint}?"
        # append formatted args
        url += "&".join(map(lambda v: f"{v[0]}={v[1]}", args.items()))

        try:
            response = requests.get(url)
        except requests.ConnectionError as e:
            return None

        if response.status_code != 200:
            return None

        data = response.json()

        if not data.get("success", False):
            return None

        return data

    def post(self, endpoint: str, data: BaseModel | dict) -> dict | None:
        """
        Send a POST requests to the api
        """
        url = f"{self.URL}{endpoint}"

        if isinstance(data, BaseModel):
            data = data.dict()

        try:
            response = requests.post(url, json=data)
        except requests.ConnectionError as e:
            return None

        if response.status_code != 200:
            return None

        data = response.json()

        if not data.get("success", False):
            return None

        return data

    def get_user_data(self, uid: str) -> UserResponse:
        """
        Return the value of the `user-data` endpoint
        """
        response = self.get("user-data", {"uid": uid})
        if response is None:
            return ResponseModel(success=False)
        return UserResponse(**response)

    def get_game_mode(
        self, id: str | None = None, all: bool | None = None
    ) -> GameModeModel | list[GameModeModel] | None:
        """
        Return the game mode with the given id
        or all the game modes (`all=True`)
        """
        if not all and id in self._game_modes.keys():
            return self._game_modes[id]

        response = self.get("game-mode", {"id": id, "all": all})
        if response is None:
            return None

        if all:
            r = AllGameModeResponse(**response)
            if r.success:
                return r.game_modes
            return []

        r = GameModeResponse(**response)
        if r.success:
            return r.game_mode
        return None

    def post_game_result(self, data: GameResultsAPI) -> GameResultsAPIResponse | None:
        """
        Post game results on the api

        Return api response
        """
        response = self.post("game-results", data)
        if response is None:
            return None

        return GameResultsAPIResponse(**response)


client = Client()
