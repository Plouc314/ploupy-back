from functools import partial
from typing import Any, Callable, Awaitable, Type
from pydantic import BaseModel, ValidationError

from src.models import core as _c, sio as _s

from .manager.usermanager import UserManager


def _dec_with_user(
    func: Callable[[str, Any], Awaitable[str]], uman: UserManager
) -> Callable[[_s.User, Any], Awaitable[str]]:
    """Implementation of `with_user`"""

    async def event(sid: str, _data: Any) -> str:
        user = uman.get_user(sid=sid)
        if user is None:
            return _c.Response(success=False, msg="User not authentificated.").json()
        return await func(user, _data)

    return event


def with_user(uman: UserManager) -> Callable[[str, Any], Awaitable[str]]:
    """
    Event function decorator

    Get the user corresponding to the `sid` argument of
    the raw event and pass it as `user` on the given function.

    Decorated function will return a `core.Response` with
    an error message in case the `sid` doesn't match a user.

    Signatures:
        - input: `(user: sio.User, ...: Any) -> str`
        - decorated: `(sid: str, ...: Any) -> str`
    """
    return partial(_dec_with_user, uman=uman)


def _dec_with_model(
    func: Callable[[Any, BaseModel], Awaitable[str]], Model: Type[BaseModel]
) -> Callable[[Any, dict], Awaitable[str]]:
    """Implementation of `with_model`"""

    async def event(_id: Any, data: dict) -> str:
        try:
            model = Model(**data)
        except ValidationError as e:
            return _c.Response(success=False, msg="Invalid data").json()
        return await func(_id, model)

    return event


def with_model(Model: Type[BaseModel]) -> Callable[[Any, dict], Awaitable[str]]:
    """
    Event function decorator

    Build an instance of the `Model` class using
    the `data` argument of the raw event and pass it
    as `model` argument on the given function.

    Decorated function will return a `core.Response` with
    an error message in case the `data` are invalid.

    Signatures:
        - input: `(...: Any, model: Model) -> str`
        - decorated: `(...: Any, data: dict) -> str`
    """
    return partial(_dec_with_model, Model=Model)
