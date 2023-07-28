"""MIT License

Copyright (c) 2017-present TwitchIO

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import datetime
import inspect
from typing import Any, Awaitable, Callable, Coroutine, TypeVar

import iso8601

__all__ = ("json_loader", "json_dumper", "copy_doc", "maybe_coro", "MISSING")

try:
    from orjson import dumps as _orjson_dumps, loads as _loads

    def _dumps(obj: dict[str, Any] | list[Any]) -> str:  # orjson returns bytes instead of str, so patch it here
        return _orjson_dumps(obj).decode()

    HAS_MODDED_JSON = True
except ModuleNotFoundError:
    try:
        from ujson import dumps as _dumps, loads as _loads

        HAS_MODDED_JSON = True
    except ModuleNotFoundError:
        from json import dumps as _dumps, loads as _loads

        HAS_MODDED_JSON = False

json_loader = _loads
json_dumper = _dumps

MISSING: Any = object()


def parse_timestamp(timestamp: str) -> datetime.datetime:
    """

    Parameters
    ----------
    timestamp: :class:`str`
        The timestamp to be parsed, in an iso8601 format.

    Returns
    -------
    :class:`datetime.datetime`
        The parsed timestamp.

    """
    return iso8601.parse_date(timestamp, datetime.timezone.utc)


T = TypeVar("T")
T_cb = TypeVar("T_cb", bound=Callable[..., Any])


def copy_doc(fn: Callable[..., Any]) -> Callable[[T_cb], T_cb]:
    """
    Copies a docstring to another function. This is a decorator.

    Parameters
    -----------
    fn: Callable
        The function to copy from.
    """

    def deco(to: T_cb) -> T_cb:
        if not fn.__doc__:
            raise TypeError(f"{fn!r} has no docstring")

        to.__doc__ = fn.__doc__
        return to

    return deco


async def maybe_coro(_fn: Callable[..., Coroutine[Any, Any, T] | Callable[..., T]], /, *args, **kwargs) -> T:
    """
    Calls a function, and awaits it if it's a coroutine.

    Parameters
    -----------
    _fn: ``Callable | Awaitable[Callable]``
        The function to call.
    *args: Any
        Any positional arguments.
    **kwargs: Any
        Any keyword arguments.
    """

    resp: Any = _fn(*args, **kwargs)

    if inspect.isawaitable(resp):
        resp = await resp

    return resp
