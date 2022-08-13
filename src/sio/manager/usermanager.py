from src.models import core as _c, sio as _s

from .manager import Manager
from ..sio import sio
from ..client import client


class UserManager(Manager):
    """
    Manager of socket-io user sessions
    """

    def __init__(self):
        self._users: dict[str, _s.User] = {}
        self._visitors: dict[str, _s.Visitor] = {}

    async def connect(
        self, sid: str, firebase_jwt: str | None = None, bot_jwt: str | None = None
    ) -> _s.User | _s.Visitor:
        """
        - Verify jwt auth
        - If auth successful get user data
        - Build and add a new sio.User/sio.Visitor instance
        - If user, broadcast user connection

        Return the sio.User / sio.Visitor
        """
        response = await client.get_user_auth(
            firebase_jwt=firebase_jwt,
            bot_jwt=bot_jwt,
        )
        if response is None:
            visitor = _s.Visitor(sid=sid)
            self._visitors[sid] = visitor
            return visitor

        response = await client.get_user_data(response.uid)
        if response is None:
            visitor = _s.Visitor(sid=sid)
            self._visitors[sid] = visitor
            return visitor

        user_sio = _s.User(sid=sid, user=response.user)
        self._users[sid] = user_sio

        await sio.emit("man_user_state", self.get_user_response(user_sio, True).json())

        return user_sio

    async def disconnect(self, pers: _s.Person):
        """
        - Remove the user/visitor from the UserManager
        - If user, broadcast user disconnection
        """
        if isinstance(pers, _s.Visitor):
            self._visitors.pop(pers.sid, None)

        if isinstance(pers, _s.User):
            self._users.pop(pers.sid, None)

            await sio.emit("man_user_state", self.get_user_response(pers, False).json())

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

    def get_visitor(self, sid: str) -> _s.Visitor | None:
        """
        Get the sio visitor with given sid,
        return None if visitor not found
        """
        return self._visitors.get(sid, None)

    def get_person(self, sid: str) -> _s.Person | None:
        """
        Get the sio person (user/visitor) with given sid,
        return None if person not found
        """
        return self.get_user(sid=sid) or self.get_visitor(sid)  # syntaxic sugar...

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
