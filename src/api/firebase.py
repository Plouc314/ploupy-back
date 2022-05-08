import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from src.core import User


class Firebase:

    PATH_ACCOUNT_KEY = "data/service_account_key.json"
    URL_DATABASE = (
        "https://ploupy-6550c-default-rtdb.europe-west1.firebasedatabase.app/"
    )

    def __init__(self):
        self._initialized = False
        self._cache_users: dict[str, User] = {}
        self.auth()

    def auth(self):
        """
        Authentificate to firebase
        Must be done before using firebase
        """

        if self._initialized:
            return
        self._initialized = True

        cred = credentials.Certificate(self.PATH_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred, {"databaseURL": self.URL_DATABASE})

    def create_user(self, user: User) -> None:
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
    ) -> User | None:
        """
        Get the user from the db given the uid or username
        """

        if uid is not None:
            # look in cache
            if uid in self._cache_users.keys():
                return self._cache_users[uid]
            
            # fetch data
            data = db.reference(f"/users/{uid}").get()

            if data is None:
                return None

            data["uid"] = uid
            user = User(**data)

            self._cache_users[uid] = user
            return user

        if username is not None:
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
            user = User(**data)

            self._cache_users[uid] = user
            return user

        return None
        
