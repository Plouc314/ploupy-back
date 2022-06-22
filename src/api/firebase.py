import os
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from src.models import core
from src.core import FirebaseException, FLAG_DEPLOY


if not FLAG_DEPLOY:
    load_dotenv()


class Firebase:

    URL_DATABASE = os.environ["URL_DATABASE"]

    def __init__(self):
        self._initialized = False
        self._cache_users: dict[str, core.User] = {}
        self.auth()

        self._config = self.load_config()
        # list of game modes ids
        self._gmids = [mode.id for mode in self._config.modes]

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

    def load_config(self) -> core.DBConfig:
        """
        Load the config node of the db
        """
        # load data
        raw = db.reference(f"/config").get()

        # build Config
        data: dict = raw["modes"]
        modes = []
        for _id, raw_mode in data.items():
            mode = core.GameMode(id=_id, **raw_mode)
            modes.append(mode)

        return core.DBConfig(modes=modes)

    def get_game_modes(self) -> list[core.GameMode]:
        """
        Return all game modes
        """
        return self._config.modes

    def get_game_mode(
        self, id: str | None = None, name: str | None = None
    ) -> core.GameMode | None:
        """
        Return the game mode with the given id / name
        """
        for mode in self._config.modes:
            if mode.id == id or mode.name == name:
                return mode
        return None

    def create_user(self, user: core.User) -> None:
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
        error: str="ignore"
    ) -> core.User | None:
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
                if error == "ignore":
                    return None
                else:
                    raise FirebaseException(f"User data not found for uid: '{uid}'")

            data["uid"] = uid
            user = core.User(**data)

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
                if error == "ignore":
                    return None
                else:
                    raise FirebaseException(f"No user found with username: '{username}'")

            for uid, data in results.items():
                data["uid"] = uid
                break
            user = core.User(**data)

            self._cache_users[uid] = user
            return user

        return None
