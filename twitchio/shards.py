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

import asyncio
import logging
import inspect
from typing import TYPE_CHECKING, Iterable

from .limiter import IRCRateLimiter
from .websocket import Websocket

if TYPE_CHECKING:
    from typing_extensions import Self
    from .tokens import BaseTokenHandler
    from .client import Client

logger = logging.getLogger("twitchio.shards")

class BaseShardManager:
    """
    This is an advanced subclassable object that can be passed to your :class:`~twitchio.Client` or :class:`~twitchio.ext.commands.Bot`.

    .. versionadded:: 3.0

    Attributes
    -----------
    tkn_mgr: :class:`TokenManager <twitchio.BaseTokenManager>`
        Your :class:`~twitchio.Client`'s token manager.
    client: :class:`~twitchio.Client`
        The client for this shard manager.
    shards: dict[:class:`str`: :class:`Shard`]
        The shards this shard manager has control over.
    initial_channels: list[:class:`str`]
        The initial channels passed to the :class:`~twitchio.Client` or :class:`~twitchio.ext.commands.Bot`.
        Callables passed to the :class:`~twitchio.Client`/:class:`~twitchio.ext.commands.Bot` will have been transformed
        into a list of channels by this point.
        If you haven't passed any initial channels, this will be ``None``.
    """
    tkn_mgr: BaseTokenHandler
    client: Client
    shards: dict[str, Shard]
    initial_channels: list[str] | None

    def __init__(self, **kwargs) -> None:
        """
        Initialize the shard manager.

        Parameters
        -----------
        \\*\\*kwargs: dict[:class:`str`: Any]
            The kwargs passed to the :class:`~twitchio.Client`/:class:`~twitchio.ext.commands.Bot`.
        """
        pass

    @classmethod
    async def _prepare(cls, tokens: BaseTokenHandler, client: Client) -> Self:
        self = cls.__new__(cls)

        self.shards = dict()
        self.tkn_mgr = tokens
        self.client = client
        self.initial_channels = await self._unwrap_initial_channels()

        self.__init__(**client._kwargs)
        await self.setup(**client._kwargs)

        return self
    
    async def _assign_initial_channels(self) -> None:
        if self.initial_channels:
            for channel in self.initial_channels:
                try:
                    await self.assign_shard(channel)
                except Exception as e:
                    logger.warning(f"An error was raised when attempting to assign channel {channel} to a shard. The channel has been discarded.", exc_info=e)
                    self.client.dispatch_listeners("error", e)
    
    async def _unwrap_initial_channels(self) -> list[str] | None:
        wrapped: list[str] = self.client._initial_channels # type: ignore

        if wrapped is None:
            return None

        if callable(wrapped):
            wrapped = wrapped()

        if inspect.isawaitable(wrapped):
            wrapped = await wrapped
        
        return list(wrapped)
    
    def add_shard(self, shard_id: str, authorized_user: str | None, *, initial_channels: Iterable[str] | None = None) -> Shard:
        """
        Adds a shard to the manager. This method does not start the shard, to do that, use :meth:`Shard.start`
        
        Parameters
        -----------
        shard_id: :class:`str`
            The unique ID to refer to this shard by. It must be unique to this manager.
        authorized_user: :class:`str` | ``None``
            The user to sign in as. You **must** have a user token for this username.
        initial_channels: list[:class:`str`] | ``None``
            The initial channels this websocket should connect to.
        
        Returns
        --------
            :class:`Shard`
                The shard instance that was created.
        """
        ws = Websocket(
            self.tkn_mgr,
            self.client,
            IRCRateLimiter(status="user", bucket="joins"),
            shard_id,
            authorized_user,
            initial_channels=initial_channels
        )

        shard = Shard(ws, shard_id)
        self.shards[shard_id] = shard
        return shard
    
    async def start_all_shards(self) -> None:
        """|coro|
        
        A helper method to start all shards that have not yet been started.
        """
        for shard in self.shards.values():
            if not shard.websocket.is_connected:
                await shard.start(block=False)
    
    async def wait_until_exit(self) -> None:
        """|coro|

        Helper function that blocks until all shards exit.
        """

        while True:
            # while we could do this as an asyncio.gather for the existing shards,
            # that would ignore all shards added after this is called.
            # instead, we opt for the loop with a one second delay.

            await asyncio.sleep(1)

            if all(x.closing for x in self.shards.values()):
                break
    
    # XXX methods to be overridden

    async def setup(self, **kwargs) -> None:
        """|coro|
        
        Method to be overriden in a subclass.

        This is a setup hook that should be used to create shards, but not start them.

        Parameters
        -----------
        \\*\\*kwargs: dict[:class:`str`: Any]
            The kwargs passed to the :class:`~twitchio.Client`/:class:`~twitchio.ext.commands.Bot`.
        """
        pass
    
    async def assign_shard(self, channel_name: str) -> None:
        """|coro|
        
        Method to be overriden in a subclass.

        This needs to be implemented to assign a channel to a shard (otherwise channels cannot be joined).
        This will be called in-between :meth:`setup` and :meth:`start`.

        .. note::
            The channel should be assigned inside of this callback.

        Parameters
        -----------
        channel_name: :class:`str`
            The channel that needs to be joined.
        """
        raise NotImplementedError

    async def start(self) -> None:
        """|coro|

        Method to be overriden in a subclass.

        This method is called when :meth:`Client/Bot.start <twitchio.Client.start>` is called.
        It should be used to start shards, and should wait until they've all exited before returning.
        You can use :meth:`await self.wait_until_exit <wait_until_exit>` to do this easily.
        """
        raise NotImplementedError
    
    async def stop(self) -> None:
        """|coro|
        
        Method to be overriden in a subclass.

        This method is called when :meth:`Client/Bot.stop <twitchio.Client.stop>` is called.
        """
        raise NotImplementedError


class DefaultShardManager(BaseShardManager):
    """
    The default shard manager.
    This will be used by default if no other shard manager is passed to :class:`~twitchio.Client`.

    .. versionadded:: 3.0

    Attributes
    -----------
    tkn_mgr: :class:`TokenManager <twitchio.BaseTokenManager>`
        Your :class:`~twitchio.Client`'s token manager.
    client: :class:`~twitchio.Client`
        The client for this shard manager.
    shards: dict[:class:`str`: :class:`Shard`]
        The shards this shard manager has control over.
    initial_channels: list[:class:`str`]
        The initial channels passed to the :class:`~twitchio.Client` or :class:`~twitchio.ext.commands.Bot`.
        Callables passed to the :class:`~twitchio.Client`/:class:`~twitchio.ext.commands.Bot` will have been transformed
        into a list of channels by this point.
        If you haven't passed any initial channels, this will be ``None``.
    """
    main_shard: Shard

    async def setup(self, **kwargs) -> None:
        _, user = await self.tkn_mgr._client_get_irc_login(self.client, None) # type: ignore

        assert user.name
        self.main_shard = self.add_shard(user.name, user.name)
    
    async def assign_shard(self, channel_name: str) -> None:
        await self.main_shard.add_channels((channel_name,))
    
    async def start(self) -> None:
        await self.main_shard.start(block=True)
    
    async def stop(self) -> None:
        await self.main_shard.stop()


class Shard:
    """
    A websocket shard. This is not to be confused with a websocket itself, however you can access the websocket via ``shard.websocket``.

    .. versionadded:: 3.0

    Attributes
    ------------
    websocket: ``twitchio.websocket.Websocket``
        The websocket itself.
    """
    __slots__ = ("websocket", "_id", "_run_task")

    def __init__(self, ws: Websocket, shard_id: str, autostart: bool = False):
        self.websocket: Websocket = ws
        self._id: str = shard_id
        self._run_task: asyncio.Task | None = None

    @property
    def id(self) -> str:
        """Returns the shard ID."""
        return self._id

    @property
    def channels(self) -> set[str]:
        """Returns the channels associated with the shard."""
        return self.websocket._channels

    @property
    def ready(self) -> bool:
        """Returns a bool indicating whether the shard is in a ready state."""
        return self.websocket._shard_ready.is_set()
    
    @property
    def closing(self) -> bool:
        """Returns a bool indicating whether the shard is closing"""
        return self.websocket.closing.is_set()
    
    async def stop(self) -> None:
        """|coro|
        
        Stops the shard, disconnecting from twitch and stopping flow of events.
        """
        
        if not self._run_task:
            raise RuntimeError("The websocket has not been started.")
        
        await self.websocket.close()
            
    async def start(self, block: bool = True) -> None:
        """|coro|

        Starts the shard, initializing its connection to twitch.

        Parameters
        -----------
        block: :class:`bool`
            Should this block until the websocket returns or not. Defaults to ``True``.
        """
        if self.websocket.is_connected:
            raise RuntimeError("This websocket cannot be started. Perhaps it has already been started?")
        
        task = asyncio.create_task(self.websocket.start_connection())
        self._run_task = task

        if block:
            try:
                await task
            finally:
                self._run_task = None

    async def add_channels(self, channel_names: Iterable[str]) -> None:
        """|coro|
        
        Add channels to this shard. This will join their chats
        """
        if not self.websocket.is_connected:
            self.websocket._channels.update(channel_names)
        else:
            await self.websocket.join_channels(channel_names)
