from src.core import UserModel

from .models import UserSioModel


class UserManager:
    def __init__(self):
        self._users: dict[str, UserSioModel] = {}

    def get_user(
        self, sid: str | None = None, username: str | None = None
    ) -> UserSioModel | None:
        '''
        Get a sio user either by sid or username,
        return None if user not found
        '''
        if sid is not None:
            return self._users.get(sid, None)
        if username is not None:
            for user in self._users.values():
                if user.user.username == username:
                    return user
            return None
        return None

    def add_user(self, sid: str, user: UserModel) -> UserSioModel:
        """
        Build and add a new UserSioModel instance from the given user
        Return the UserSioModel
        """
        user_sio = UserSioModel(sid=sid, user=user)
        self._users[sid] = user_sio
        return user_sio

    def remove_user(self, sid: str):
        """
        Remove the user from the UserManager
        """
        self._users.pop(sid, None)
