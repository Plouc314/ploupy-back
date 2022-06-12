from dataclasses import dataclass
import os
from typing import TypedDict
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from src.core import GameConfig, UserModel, FLAG_DEPLOY


if not FLAG_DEPLOY:
    load_dotenv()


@dataclass
class CacheConfig:
    game_config: GameConfig | None=None


class Firebase:

    URL_DATABASE = os.environ["URL_DATABASE"]

    def __init__(self):
        self._initialized = False
        self._cache_users: dict[str, UserModel] = {}
        self._cache_config = CacheConfig()
        self.auth()

    @staticmethod
    def _get_certificate() -> dict:
        """
        Load the firebase credentials for environment variables
        """
        keys = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_x509_cert_url",
        ]
        cert = {}

        for key in keys:
            value = os.environ[f"firebase_{key}".upper()]
            cert[key] = value

        return cert

    def auth(self):
        """
        Authentificate to firebase
        Must be done before using firebase
        """

        if self._initialized:
            return
        self._initialized = True

        cred = credentials.Certificate(self._get_certificate())
        firebase_admin.initialize_app(cred, {"databaseURL": self.URL_DATABASE})

    def create_user(self, user: UserModel) -> None:
        """
        Create a user in the db
        """
        # build dict without uid
        data = user.dict()
        data.pop("uid")

        # push to db
        db.reference(f"/users/{user.uid}").set(data)

        # add to cache
        self._cache_users[user.uid] = user

    def get_user(
        self,
        uid: str | None = None,
        username: str | None = None,
    ) -> UserModel | None:
        """
        Get the user from the db given the uid or username
        """

        if uid is not None and uid != "":
            # look in cache
            if uid in self._cache_users.keys():
                return self._cache_users[uid]

            # fetch data
            data = db.reference(f"/users/{uid}").get()

            if data is None:
                return None

            data["uid"] = uid
            user = UserModel(**data)

            self._cache_users[uid] = user
            return user

        if username is not None and username != "":
            # look in cache
            for user in self._cache_users.values():
                if user.username == username:
                    return user

            # fetch data
            results = (
                db.reference("/users")
                .order_by_child("username")
                .equal_to(username)
                .get()
            )

            if len(results) == 0:
                return None

            for uid, data in results.items():
                data["uid"] = uid
                break
            user = UserModel(**data)

            self._cache_users[uid] = user
            return user

        return None

    def get_game_config(self, with_cache: bool=True) -> GameConfig:
        '''
        Load the game config from the db,
        if `with_cache=True`, use a cache
        '''
        if with_cache and self._cache_config.game_config is not None:
            return self._cache_config.game_config

        data = db.reference(f"/config/game-config").get()

        config = GameConfig(**data)

        # store in cache
        self._cache_config.game_config = config

        return config