import json
import os
import uuid
import jwt
from datetime import datetime, timezone

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db, auth
from ..core.exceptions import BotCreationException, InvalidUsernameException

from src.models import core as _c
from src.core import FirebaseException, AuthException

MAX_BOT_PER_USER = 5
MIN_LEN_USERNAME = 5


class Firebase:

    URL_DATABASE = os.environ["URL_DATABASE"]
    SIO_TOKEN = os.environ["SIO_TOKEN"]

    def __init__(self):
        self._initialized = False
        # key: token value: uid
        self._cache_fb_tokens: dict[str, str] = {}
        # key: uid
        self._cache_users: dict[str, _c.User] = {}
        self.auth()

        self._config = self.load_config()
        # list of game modes ids
        self._gmids = [mode.id for mode in self._config.modes]

    @staticmethod
    def _get_certificate() -> dict:
        """
        Load the firebase credentials from environment variable
        """
        return json.loads(os.environ["FIREBASE_CREDENTIALS"])

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

    def load_config(self) -> _c.DBConfig:
        """
        Load the config node of the db
        """
        # load data
        raw = db.reference(f"/config").get()

        # build Config
        data: dict = raw["modes"]
        modes = []
        for _id, raw_mode in data.items():
            mode = _c.GameMode(id=_id, **raw_mode)
            modes.append(mode)

        return _c.DBConfig(modes=modes)

    def get_game_modes(self) -> list[_c.GameMode]:
        """
        Return all game modes
        """
        return self._config.modes

    def get_game_mode(
        self, id: str | None = None, name: str | None = None
    ) -> _c.GameMode | None:
        """
        Return the game mode with the given id / name
        """
        for mode in self._config.modes:
            if mode.id == id or mode.name == name:
                return mode
        return None

    def auth_sio_client(self, siotk: str) -> bool:
        """
        Verify the sio client token

        Return if it is valid
        """
        return siotk == self.SIO_TOKEN

    def auth_firebase_jwt(self, token: str) -> str | None:
        """
        Verify that the given id token is valid

        Return the user's `uid` if valid, None otherwise
        """
        # look in cache
        if token in self._cache_fb_tokens.keys():
            return self._cache_fb_tokens[token]

        try:
            response = auth.verify_id_token(token)
            uid = response["uid"]

        # there is about a million things that could go wrong...
        except Exception as e:
            print(f"WARGING AUTH: {type(e)} {str(e)}")
            return None

        # update cache
        self._cache_fb_tokens[token] = uid

        return uid

    def auth_bot_jwt(self, token: str) -> str:
        """
        Assert that the given token is valid

        Return the user's `uid`

        Raises AuthException if the token is invalid
        """
        headers = jwt.get_unverified_header(token)
        uid = headers.get("uid", None)
        if uid is None:
            raise AuthException("Header 'uid' not provided.")

        # get key from db
        key = db.reference(f"/keys/{uid}/bot_key").get()
        if key is None:
            raise AuthException(f"No key for given uid.")

        try:
            jwt.decode(token, key, algorithms="HS256")
        except jwt.exceptions.InvalidSignatureError:
            raise AuthException("Invalid key")

        return uid

    def create_bot_jwt(self, bot: _c.User, keys: _c.UserKeys) -> str:
        """
        Create the jwt token for the given key
        """
        return jwt.encode({}, keys.bot_key, algorithm="HS256", headers={"uid": bot.uid})

    def assert_username_valid(self, username: str) -> None:
        """
        Raises InvalidUsernameException if the username is invalid
        """
        # assert min length
        if len(username) < MIN_LEN_USERNAME:
            raise InvalidUsernameException(f"Username {username} is too short.")

        # assert username unicity
        existing_user = self.get_user(username=username)
        if existing_user is not None:
            raise InvalidUsernameException(f"Username {username} is already taken.")

    def create_user(self, user: _c.User) -> None:
        """
        Create a user in the db.

        NOTE: no assertions are performed
        """
        # build dict without uid
        # rely on pydantic for datetime conversions (NOPE)
        data = user.dict()
        data.pop("uid")
        data["joined_on"] = data["joined_on"].isoformat()
        data["last_online"] = data["last_online"].isoformat()

        # push to db
        db.reference(f"/users/{user.uid}").set(data)

        # add to cache
        self._cache_users[user.uid] = user

    def _cast_db_user(self, uid: str, raw: dict) -> _c.User:
        """
        Cast raw db data to user
        """
        # add potentially missing fields
        raw = {"uid": uid, "owner": None, "bots": []} | raw
        return _c.User(**raw)

    def get_user(
        self, uid: str | None = None, username: str | None = None, error: str = "ignore"
    ) -> _c.User | None:
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

            user = self._cast_db_user(uid, data)

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
                    raise FirebaseException(
                        f"No user found with username: '{username}'"
                    )

            for uid, data in results.items():
                break
            user = self._cast_db_user(uid, data)

            self._cache_users[uid] = user
            return user

        return None

    def create_bot(self, user: _c.User, username: str) -> tuple[_c.User, str]:
        """
        Create a bot in the db if possible

        Returns the bot's user, the bot jwt token

        Raises BotCreationException if not possible
        """
        # assert do not cross bots limit
        if len(user.bots) >= MAX_BOT_PER_USER:
            raise BotCreationException("Maximum bots limit reached.")

        self.assert_username_valid(username)

        # create bot user
        uid = uuid.uuid4().hex
        bot = _c.User(
            uid=uid,
            username=username,
            email=user.email,
            avatar="penguin",
            is_bot=True,
            owner=user.uid,
            bots=[],
            joined_on=datetime.now(tz=timezone.utc),
            last_online=datetime.now(tz=timezone.utc),
        )

        # push it to db
        self.create_user(bot)

        # create bot key
        keys = _c.UserKeys(bot_key=uuid.uuid4().hex)
        # push them to db
        db.reference(f"/keys/{uid}").set(keys.dict())

        # add bot to user
        user.bots.append(uid)

        # update user on db
        db.reference(f"users/{user.uid}/bots").set(user.bots)

        return bot, self.create_bot_jwt(bot, keys)

    def update_last_online(self, uid: str, last_online: datetime):
        """
        Update the `User.last_online` field of the db for the given uid

        Update the users's cache, meaning the caller posseses an instance of the user,
        it might modify its `last_online` attribute.

        Raise FirebaseException in case the uid is invalid
        """
        # assert uid is valid
        user = self.get_user(uid=uid)
        if user is None:
            raise FirebaseException(f"Invalid uid: '{uid}'")

        # update user instance
        user.last_online = last_online

        data = last_online.isoformat()
        # push to db
        db.reference(f"/users/{uid}/last_online").set(data)

        # update cache
        self._cache_users[uid] = user
