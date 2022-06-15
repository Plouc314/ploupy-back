import os
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from src.core import (
    ConfigModel,
    GameModeModel,
    GeneralStatsModel,
    UserStatsModel,
    UserModel,
    GameModes,
    FirebaseException,
    FLAG_DEPLOY,
)


if not FLAG_DEPLOY:
    load_dotenv()


class Firebase:

    URL_DATABASE = os.environ["URL_DATABASE"]

    def __init__(self):
        self._initialized = False
        self._cache_users: dict[str, UserModel] = {}
        self._cache_stats: dict[str, UserStatsModel] = {}
        self.auth()

        self._config = self.load_config()
        # list of game modes names
        self._game_modes = [mode.name for mode in self._config.modes]

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

    def load_config(self) -> ConfigModel:
        """
        Load the config node of the db
        """
        # load data
        raw = db.reference(f"/config").get()

        # build ConfigModel
        data: dict = raw["modes"]
        modes = []
        for _id, raw_mode in data.items():
            mode = GameModeModel(id=_id, **raw_mode)
            modes.append(mode)

        return ConfigModel(modes=modes)

    def get_game_modes(self) -> list[GameModeModel]:
        """
        Return all game modes
        """
        return self._config.modes

    def get_game_mode(
        self, id: str | None = None, name: str | None = None
    ) -> GameModeModel | None:
        """
        Return the game mode with the given id / name
        """
        for mode in self._config.modes:
            if mode.id == id or mode.name == name:
                return mode
        return None

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
        error: str="ignore"
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
                if error == "ignore":
                    return None
                else:
                    raise FirebaseException(f"User data not found for uid: '{uid}'")

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
                if error == "ignore":
                    return None
                else:
                    raise FirebaseException(f"No user found with username: '{username}'")

            for uid, data in results.items():
                data["uid"] = uid
                break
            user = UserModel(**data)

            self._cache_users[uid] = user
            return user

        return None

    def _get_default_genstats(self, mode: GameModeModel) -> GeneralStatsModel:
        """
        Build GeneralStatsMode instance for given mode with default values
        """
        # build general stats with 0 occurence in all possible positions
        return GeneralStatsModel(
            mode=mode,
            mmr=100,
            scores=[0 for n in range(mode.config.n_player)],
        )

    def get_user_stats(self, uid: str) -> UserStatsModel:
        """
        Get the user stats from the db
        
        Assume the uid is valid.
        """
        # look in cache
        if uid in self._cache_stats.keys():
            return self._cache_stats[uid]

        # fetch data
        data: dict = db.reference(f"/stats/{uid}").get()

        if data is None:
            stats = UserStatsModel(
                uid=uid,
                stats={
                    mode.name: self._get_default_genstats(mode)
                    for mode in self._config.modes
                },
            )

        else:
            # build UserStats (see schemas.d.ts for db structure)
            user_stats = {}

            # build using db data
            for _id, stats in data.items():

                # get game mode
                mode = self.get_game_mode(id=_id)

                genstats = GeneralStatsModel(
                    mode=mode,
                    mmr=stats["mmr"],
                    scores=stats["scores"],
                )
                user_stats[mode.name] = genstats

            # fill potentially missing data
            for game_mode in self._game_modes:
                if not game_mode in user_stats.keys():
                    mode = self.get_game_mode(name=game_mode)
                    user_stats[mode.name] = self._get_default_genstats(mode)

            stats = UserStatsModel(uid=uid, stats=user_stats)

        # update cache
        self._cache_stats[uid] = stats
        return stats

    def update_user_stats(
        self,
        user_stats: UserStatsModel | None = None,
        uid: str | None = None,
        gmid: str | None = None,
        stats: GeneralStatsModel | None = None,
    ):
        """
        Update the user stats by giving one of:
        - `user_stats`
            Update all the stats
        - `uid`, `gmid`, `stats`
            Update the stats for one mode
        """
        if user_stats is not None:
            # build db data
            data = {}
            for genstats in user_stats.stats.values():
                data[genstats.mode.id] = {
                    "mmr": genstats.mmr,
                    "scores": genstats.scores,
                }

            # push to db
            db.reference(f"/stats/{user_stats.uid}").set(data)

            # update cache
            self._cache_stats[uid] = user_stats

        elif not None in (uid, gmid, stats):

            game_mode = self.get_game_mode(id=gmid)

            if game_mode is None:
                raise FirebaseException(f"Invalid game mode id '{gmid}'")

            # build db data
            data = {
                "mmr": stats.mmr,
                "scores": stats.scores,
            }

            # push to db
            db.reference(f"/stats/{uid}/{game_mode.id}").set(data)

            # update cache
            self._cache_stats[uid].stats[game_mode.name] = stats
