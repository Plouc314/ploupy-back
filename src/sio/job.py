import inspect
from typing import AsyncGenerator
from pydantic import BaseModel

from .sio import sio


class Job:
    def __init__(
        self, jb: "JobManager", event: str, behaviour: AsyncGenerator[BaseModel, None]
    ):
        self.jb = jb
        self.event = event
        """Name of the event emitted to the client"""
        self.behaviour = behaviour

    def _build_job(self):
        """ """
        # check if the "jb" arg is defined
        # if it is: pass the job manager as "jb" kwarg
        sig = inspect.signature(self.behaviour)
        sup_kwargs = {}
        if "jb" in sig.parameters or "kwargs" in sig.parameters:
            sup_kwargs["jb"] = self.jb

        async def job(*args, **kwargs):
            async for data in self.behaviour(*args, **sup_kwargs | kwargs):
                await sio.emit(self.event, data.dict(), to=self.jb.gid)

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

    def send(self, event: str, data: BaseModel) -> None:
        """
        Send an event
        """

        async def behaviour():
            yield data

        job = self.make_job(event, behaviour)
        job.start()

    def make_job(self, event: str, behaviour: AsyncGenerator[BaseModel, None]) -> Job:
        """
        Create a new Job instance
        behaviour: if it defines a "jb" argument, the JobManager instance will
            be passed as keyword argument
        """
        return Job(self, event, behaviour)

    @classmethod
    async def sleep(cls, t: float):
        await sio.sleep(t)
