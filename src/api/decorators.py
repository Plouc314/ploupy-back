import logging
from functools import wraps
from typing import Callable

from pydantic import BaseModel

logger = logging.getLogger("ploupy")


def with_logger(func: Callable) -> Callable:
    @wraps(func)
    def inner(*args, **kwargs):

        outs = [f"[{func.__name__}]"]
        for key, value in kwargs.items():
            if not isinstance(value, BaseModel) and value is not None:
                value = str(value)
                if len(value) > 30:
                    value = value[:27] + "..."
                outs.append(f"{key}={value}")

        logger.info(" ".join(outs))

        return func(*args, **kwargs)

    return inner
