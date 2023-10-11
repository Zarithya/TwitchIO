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
from __future__ import annotations

from typing import TYPE_CHECKING
from .abc import Messageable

if TYPE_CHECKING:
    from .websocket import Websocket
    from .shards import BaseShardManager

__all__ = ("Channel",)


class Channel(Messageable):
    __slots__ = ("_name", "_id", "_shard_manager", "_target_ws")

    def __init__(self, id: int | None, name: str, shard_manager: BaseShardManager):
        super().__init__(name=name, shard_manager=shard_manager)
        self._id: int | None = id
        self._target_ws: Websocket | None = None

    def __repr__(self) -> str:
        return f"<Channel: name={self._name}>"

    async def send(self, content: str) -> None:
        """|coro|
        Sends a whisper message to the channel's user.

        Parameters
        -----------
        content: :class:`str`
            The content to send to the user
        """
        if not self._target_ws:
            self._target_ws = (await self._shard_manager.get_sender_shard(self._name)).websocket
        
        await self._target_ws.send(f"PRIVMSG #{self._name} :{content}")

    @property
    def name(self) -> str:
        """
        The channel name.

        Returns
        --------
        :class:`str`
        """
        return self._name

    @property
    def id(self) -> int | None:
        """
        The channel ID.

        Returns
        --------
        :class:`int` | ``None``
        """
        return self._id and int(self._id)
