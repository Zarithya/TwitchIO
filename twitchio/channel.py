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
import copy

from .abc import Messageable

__all__ = ("Channel",)


class Channel(Messageable):
    __slots__ = ("_name", "_id", "_websocket")

    def __init__(self, **attrs):
        super().__init__(**attrs)
        self._id: int | None = attrs.get("id")

    def __repr__(self) -> str:
        return f"<Channel: name={self._name}, shard_index={self._websocket.shard_index}>"

    async def send(self, content: str) -> None:
        """|coro|
        Sends a whisper message to the channel's user.

        Parameters
        -----------
        content: :class:`str`
            The content to send to the user
        """
        await self._websocket.send(f"PRIVMSG #{self._name} :{content}")

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
