from typing import AsyncGenerator
from pydantic import BaseModel

from .sio import sio


class Job:
    def __init__(
        self, gid: str, event: str, behaviour: AsyncGenerator[BaseModel, None]
    ):
        self.gid = gid
        self.event = event
        """Name of the event emitted to the client"""
        self.behaviour = behaviour

    def _build_job(self):
        """ """
        async def job(*args, **kwargs):
            async for data in self.behaviour(*args, **kwargs):
                await sio.emit(self.event, data.dict(), to=self.gid)
        return job

    def start(self, *args, **kwargs):
        """
        Start the job
        """
        sio.start_background_task(self._build_job(), *args, **kwargs)

    @classmethod
    async def sleep(cls, t: float):
        await sio.sleep(t)

class JobManager:
    
    def __init__(self, gid: str) -> None:
        self.gid = gid

    def make_job(self, event: str, behaviour: AsyncGenerator[BaseModel, None]) -> Job:
        '''
        Create a new Job instance
        '''
        return Job(self.gid, event, behaviour)

    @classmethod
    async def sleep(cls, t: float):
        await sio.sleep(t)