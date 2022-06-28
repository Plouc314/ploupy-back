import inspect
from typing import AsyncGenerator, Callable, Coroutine
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
                await sio.emit(self.event, data.json(), to=self.jb.gid)

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

    def execute(
        self,
        func: Coroutine,
        delay: float = 0,
    ):
        """
        Execute the given `func` (must be an aysnc function)
        after the given delay.
        """

        async def job():
            if delay > 0:
                await self.sleep(delay)
            await func()

        sio.start_background_task(job)

    def send(
        self,
        event: str,
        data: BaseModel,
        delay: float = 0,
        on_send: Callable | None = None,
    ) -> None:
        """
        Send an event (ONLY to the users in game)

        Create a job that broadcast the message,
        if `delay > 0`, wait for the `delay` before sending the message

        If given, the `on_send` callback will be called after the message was sent
        """

        async def behaviour():
            if delay > 0:
                await self.sleep(delay)
            yield data

            if on_send is not None:
                on_send()

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
