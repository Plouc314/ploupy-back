from abc import ABC, abstractmethod

from src.models import sio as _s


class Manager(ABC):
    """
    Manager abstract class

    Represents stateful manager used in singleton-like pattern
    """

    @abstractmethod
    async def connect(self):
        """
        Called on user connection (in connect sio-event)
        """

    @abstractmethod
    async def disconnect(self, user: _s.User):
        """
        Called on user disconnection (in disconnect sio-event)
        """

    @property
    @abstractmethod
    def state(self):
        """
        Return the manager state with all the data (not a partial state)
        """
