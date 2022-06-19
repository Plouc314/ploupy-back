from src.models import core, sio


class UserManager:
    def __init__(self):
        self._users: dict[str, sio.User] = {}

    def get_user(
        self, sid: str | None = None, username: str | None = None
    ) -> sio.User | None:
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

    def add_user(self, sid: str, user: core.User) -> sio.User:
        """
        Build and add a new sio.User instance from the given user
        Return the sio.User
        """
        user_sio = sio.User(sid=sid, user=user)
        self._users[sid] = user_sio
        return user_sio

    def remove_user(self, sid: str):
        """
        Remove the user from the UserManager
        """
        self._users.pop(sid, None)
