import os
import socket
import aiohttp
from dotenv import load_dotenv
from pydantic import BaseModel

from src.models import core as _c, sio as _s
from src.models.api import args, responses

from src.core import FLAG_DEPLOY


if not FLAG_DEPLOY:
    load_dotenv()


class Client:
    """Client to the main api"""

    URL_DEV = "http://127.0.0.1:5000/api/"
    URL_DEPLOY = "https://ploupy-api-production.up.railway.app/api/"
    URL = URL_DEPLOY if FLAG_DEPLOY else URL_DEV

    SIO_TOKEN = os.environ["SIO_TOKEN"]

    def __init__(self):

        # wait to create session instance inside a async func
        # https://stackoverflow.com/questions/52232177/runtimeerror-timeout-context-manager-should-be-used-inside-a-task
        self.session: aiohttp.ClientSession = None
        self._game_modes: dict[str, _c.GameMode] = {}

    async def get(self, endpoint: str, **kwargs) -> dict | None:
        """
        Send a GET requests to the api
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()

        url = f"{self.URL}{endpoint}?"
        # append formatted args
        url += "&".join((f"{k}={v}" for k, v in kwargs.items() if v is not None))

        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.json()
        except aiohttp.ClientError as e:
            print("WARNING GET", type(e), e)
            return None

        if not data.get("success", False):
            return None

        return data

    async def post(self, endpoint: str, data: BaseModel | dict) -> dict | None:
        """
        Send a POST requests to the api

        Note: doesn't convert BaseModel data using `json()` but rather `dict()`
            thus it can not handle `datetime` attributes
        """
        if self.session is None:
            self.session = aiohttp.ClientSession()

        url = f"{self.URL}{endpoint}"

        if isinstance(data, BaseModel):
            data = data.dict()

        try:
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    return None
                data = await response.json()
        except aiohttp.ClientError as e:
            print("WARNING POST", type(e), e)
            return None

        if not data.get("success", False):
            return None

        return data

    async def get_user_auth(
        self, firebase_jwt: str | None = None, bot_jwt: str | None = None
    ) -> responses.UserAuth | None:
        """
        Return the uid corresponding to the given jwt, if valid
        """
        response = await self.get(
            "user-auth", firebase_jwt=firebase_jwt, bot_jwt=bot_jwt
        )
        if response is None:
            return None
        return responses.UserAuth(**response)

    async def post_user_online(self, user: _s.User) -> None:
        """
        Ping api on user online status
        """
        data = args.UserOnline(siotk=self.SIO_TOKEN, uid=user.user.uid)
        response = await self.post("user-online", data)

    async def get_user_data(self, uid: str) -> responses.UserData | None:
        """
        Return the value of the `user-data` endpoint
        """
        response = await self.get("user-data", uid=uid)
        if response is None:
            return None
        return responses.UserData(**response)

    async def get_game_mode(
        self, id: str | None = None, all: bool | None = None
    ) -> _c.GameMode | list[_c.GameMode] | None:
        """
        Return the game mode with the given id
        or all the game modes (`all=True`)
        """
        if not all and id in self._game_modes.keys():
            return self._game_modes[id]

        response = await self.get("game-mode", id=id, all=all)

        if response is None:
            return None

        response = responses.GameMode(**response)

        # update cache
        for mode in response.game_modes:
            if not id in self._game_modes.keys():
                self._game_modes[id] = mode

        if all:
            return response.game_modes
        return response.game_modes[0]

    async def post_game_result(
        self, gmid: str, ranking: list[str]
    ) -> responses.GameResults | None:
        """
        Post game results on the api

        Return api response
        """
        data = args.GameResults(
            siotk=self.SIO_TOKEN,
            gmid=gmid,
            ranking=ranking,
        )

        response = await self.post("game-results", data)
        if response is None:
            return None

        return responses.GameResults(**response)


client = Client()
