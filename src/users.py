from typing import OrderedDict
from firebase_admin import db

from src.models import UserModel


def create_user(user: UserModel) -> None:
    '''
    Create a user in the db
    '''
    # build dict without uid
    data = user.dict()
    data.pop("uid")
    # push to db
    db.reference(f"/users/{user.uid}").set(data)


def get_user(
    uid: str | None = None,
    username: str | None = None,
) -> UserModel | None:
    '''
    Get the user from the db given the uid or username
    '''
    data = None

    if uid is not None:
        data = db.reference(f"/users/{uid}").get()
        data["uid"] = uid

    if username is not None:
        results = db.reference("/users").order_by_child("username").equal_to(username).get()

        if len(results) == 0:
            return None
        
        for uid, data in results.items():
            data["uid"] = uid
            break

    if data is None:
        return None

    return UserModel(**data)
