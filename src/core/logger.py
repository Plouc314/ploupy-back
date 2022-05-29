import inspect
import os
from datetime import datetime
from functools import wraps, partial
from typing import Callable


class LogConfig:
    root_path: str = "logs"
    default_name: str = "base"


class _LoggerDecorator:
    '''
    Decorator
    '''
    
    def _write(self, name: str, msg: str):
        '''
        Write the logging message to the output
        '''
        filename = os.path.join(LogConfig.root_path, f"{name}.log")
        with open(filename, "a") as file:
            file.write(msg)

    def _get_date(self) -> str:
        return datetime.now().strftime("[%d-%m-%y %M:%S]")

    def _get_header(self, func: Callable) -> str:
        header = self._get_date()
        header += "  "
        header += func.__name__
        return header

    def _get_inputs(self, func: Callable, args: list, kwargs: dict) -> str:
        lines = []
        params = inspect.signature(func).parameters
        
        for name, value in zip(params.keys(), args):
            line = f"{name}: {value}"
            lines.append(line)
        
        for name, value in kwargs:
            line = f"{name}= {value}"
            lines.append(line)
        
        return "    Inputs:    " + ", ".join(lines)

    def _log(self, func: Callable, name: str):
        '''
        Log the function call
        '''
        @wraps(func)
        async def inner(*args, **kwargs):
            
            msg = [
                "=" * 20,
                self._get_header(func),
                self._get_inputs(func, args, kwargs),
            ]
            msg = "\n".join(msg) + "\n"
            self._write(name, msg)

            return await func(*args, **kwargs)

        return inner

    def __call__(self, value: Callable | str):

        if callable(value):
            return self._log(value, LogConfig.default_name)

        return partial(self._log, name=value)

os.makedirs(LogConfig.root_path)

logged = _LoggerDecorator()

