import requests

from src.core import ResponseModel, FLAG_DEPLOY
from src.api import UserResponse, GameConfigResponse


class Client:
    """Client to the main api"""

    URL_DEV = "http://127.0.0.1:5000/api/"
    URL_DEPLOY = "https://ploupy.herokuapp.com/api/"
    URL = URL_DEPLOY if FLAG_DEPLOY else URL_DEV

    @classmethod
    def get(cls, endpoint: str, args: dict) -> dict | None:
        """
        Send a GET requests to the api
        """
        url = f"{cls.URL}{endpoint}?"
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

    @classmethod
    def get_user_data(cls, uid: str) -> UserResponse:
        """
        Return the value of the `user-data` endpoint
        """
        response = cls.get("user-data", {"uid": uid})
        if response is None:
            return ResponseModel(success=False)
        return UserResponse(**response)

    @classmethod
    def get_default_game_config(cls) -> GameConfigResponse:
        """
        Return the value of the `default-game-config` endpoint
        """
        response = cls.get("default-game-config", {})
        if response is None:
            return ResponseModel(success=False)
        return GameConfigResponse(**response)
