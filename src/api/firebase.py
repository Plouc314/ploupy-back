import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from src.core import UserModel


class Firebase:

    URL_DATABASE = (
        "https://ploupy-6550c-default-rtdb.europe-west1.firebasedatabase.app/"
    )
    CERT = {
        "type": "service_account",
        "project_id": "ploupy-6550c",
        "private_key_id": "23ef286075eaa28274b0f2ec6217000c5038b4b0",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCLObuMeaSyfY8Q\nB7w72MqJJPV+poAGeg7UQ85t+3yHFst4UGMnfVnzDT6mIJq169IAs50RhEdgYnCk\n6Q5jrEHbALwJcZSITZJDR1WJFE+/FIkzZwaPMmxfl0R8p10YTsmqq4ZVSSRDFcEt\nRo8PeEhVnvaVoRupNXRh6bYQEDxDU6shOJzZXJ2bv6hWTwtCxOCIQ7W8cTOqIpwo\nivkjzRjnp8ALRsRNjIjDfMbRu+O9iWVHT8UyB4oOrwpwXzC4fiCvjB2GNGznXVku\nz5vLhn+dCKPcdKHNCT8wRkzNrBabanp1J6Ey1ZWCPSkw6jtf1cGBR/BhMSqg3a+f\nrN5nkLldAgMBAAECggEABcwkpCfYlNonn+pCi1dur6FLW7fBMwPYJDyilu/W8qUf\nWeY3CsjsevN9PVu0NYkZWJAiJT2V30yaFjPiNoJQx7bTHa2OGtLoGUcaJ7ghzfoj\n8HEE0+esnZpl7q7lcIKvYRz9XgXKrcR1I9aBVIqUsIQLDpYD2drw+rbJrweOCtuc\nVpSZU0OkH6sq6bG595BJYZnOFRUgJZYMDdyBmt4H2G0xJzDfXjZZFd5yrNKh8f5o\nrDAs4BjpFKUBrO63AO8guz0v689IiGjWy7R7xSwVCoUqXTk+KtYKNxMdO4qN7yo4\nKftm3LAudyJWRVKER4VOTWgp70L1RToM9CpafwiLPQKBgQC9RoMReDynu+6djmPl\n01A7Ca/DjzUMLnVsYmug4ZqhcqsVtsiYJM1VDpoWpUu6ag/YcbRmvBXkFMaijw3y\nB8qT+a9K44nngPzR+VUQD6OtLKhqt4nAg/BNffcFJFPcKoDQWFHwEBtgG+vln86e\nXQrCY3r2qJf4eI0whf9ocHu/ewKBgQC8TmEgc7OrpMjTipo464nyJUGE5twq+yRz\nCtShZKiYzznd+1+h+R6TdqQpWN+4UsjxPvd7U+l4bXhesVhhVopOS04gfugGyfcp\n0dRGWU72N4JhQdjVFUvgbNyGW2kprQde3D4FLbLgkXzApNPLWSJxBn4lNS881Yvc\nCwPLkyxnBwKBgQCUjEGTtWUNU76bY0Rd/LGsFBchCUTd8Zxw2vGTi1xbt240lYbr\neX65ccNXYJWFkXYsLlkihB0+K1wV+uY7/QdtiXmc8eWqjp5dgSzUdSHFaRYo4zE2\nqZYwi1sSawdx9N2yJo7wNQP3MxK53elAes9V7tNzwK+874gH/DKO2jEU/wKBgQCb\ntjCItkRfbh8HFnjbEqJ6UqZwMLrk69HDM7SKVQM5gTp3vjLhbHAFPrkW27/72rEB\nFLFvEP9hrxw3KW1M6FPr1EehhW92lbHFqhZfqeAqp9IvfFTCNx8MUNi2XYaDiOos\nXfEHNTfSjVvcrS/Z2jYpwlWzjNwn8On7JjyYLXYtJwKBgGRwPmz8ROoKrR0/q+JG\nNTNZF2tAUYiiTzlV5NK8pSSiGm34CsYMaD8Evd5AzGReGSZfbgBZoVqMK4SYDLk+\nDsZeM/cQfH97OudpCjjA7TiuZn+2E/qG8v198Da2R95/daiV7yBxiboOLikdzpVw\nRF2194vdT5fO3+P6Y9rZVXaO\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-kw5wq@ploupy-6550c.iam.gserviceaccount.com",
        "client_id": "109147262036596320669",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-kw5wq%40ploupy-6550c.iam.gserviceaccount.com"
    }


    def __init__(self):
        self._initialized = False
        self._cache_users: dict[str, UserModel] = {}
        self.auth()

    def auth(self):
        """
        Authentificate to firebase
        Must be done before using firebase
        """

        if self._initialized:
            return
        self._initialized = True

        cred = credentials.Certificate(self.CERT)
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
            print(data)
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
        
