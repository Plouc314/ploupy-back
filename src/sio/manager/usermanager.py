from src.models import core as _c, sio as _s

from .manager import Manager
from ..sio import sio


class UserManager(Manager):
    """
    Manager of socket-io user sessions
    """

    def __init__(self):
        self._users: dict[str, _s.User] = {}

    async def connect(self, sid: str, user: _c.User) -> _s.User:
        """
        - Build and add a new sio.User instance from the given user
        - Broadcast user connection

        Return the sio.User
        """
        user_sio = _s.User(sid=sid, user=user)
        self._users[sid] = user_sio

        await sio.emit("man_user_state", self.get_user_response(user_sio, True).dict())

        return user_sio

    async def disconnect(self, user: _s.User):
        """
        - Remove the user from the UserManager
        - Broadcast user disconnection
        """
        self._users.pop(user.sid, None)

        await sio.emit("man_user_state", self.get_user_response(user, False).dict())

    def get_user(
        self, sid: str | None = None, username: str | None = None
    ) -> _s.User | None:
        """
        Get a sio user either by sid or username,
        return None if user not found
        """
        if sid is not None:
            return self._users.get(sid, None)
        if username is not None:
            for user in self._users.values():
                if user.user.username == username:
                    return user
            return None
        return None

    def get_user_response(
        self, user: _s.User, connected: bool
    ) -> _s.responses.UserManagerState:
        """
        Return the UserManagerState for one user
        """
        return _s.responses.UserManagerState(
            users=[_s.UserState(connected=connected, user=user.user)]
        )
    
    @property
    def state(self) -> _s.responses.UserManagerState:
        return _s.responses.UserManagerState(
            users=[
                _s.UserState(connected=True, user=u.user) for u in self._users.values()
            ]
        )
