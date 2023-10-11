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

import abc
import asyncio
import logging
import inspect
import math
from typing import TYPE_CHECKING, Iterable, Protocol

from .limiter import IRCRateLimiter
from .websocket import Websocket
from .utils import PY_311

if TYPE_CHECKING:
    from typing_extensions import Self
    from .tokens import BaseTokenHandler
    from .client import Client

__all__ = (
    "Shard",
    "BaseShardManager",
    "DefaultShardManager",
    "DistributedShardManager"
)

logger = logging.getLogger("twitchio.shards")

class BaseShardManager(metaclass=abc.ABCMeta):
    """
    This is an advanced subclassable object that can be passed to your :class:`~twitchio.Client` or :class:`~twitchio.ext.commands.Bot`.

    .. versionadded:: 3.0

    Attributes
    -----------
    token_handler: :class:`TokenHandler <twitchio.BaseTokenHandler>`
        Your :class:`~twitchio.Client`'s token handler.
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
    token_handler: BaseTokenHandler
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
        try:
            self = cls.__new__(cls)
        except TypeError as e:
            if PY_311:
                e.add_note("Tip: You'll need to fill out all abstract methods.")
            
            raise
        
        self.shards = dict()
        self.token_handler = tokens
        self.client = client
        self.initial_channels = await self._unwrap_initial_channels()

        self.__init__(**client._kwargs)
        await self.setup(**client._kwargs)

        return self
    
    async def _assign_initial_channels(self) -> None:
        if self.initial_channels:
            for channel in self.initial_channels:
                try:
                    await self.assign_shard(channel, True)
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
            self.token_handler,
            self.client,
            IRCRateLimiter(status="user", bucket="joins"),
            shard_id,
            self,
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
    
    async def stop_all_shards(self) -> None:
        """|coro|
        
        A helper method to stop all shards.
        """
        for shard in self.shards.values():
            if shard.websocket.is_connected:
                await shard.stop()
    
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
    
    @abc.abstractmethod
    async def assign_shard(self, channel_name: str, is_initial_channel: bool) -> None:
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
        is_initial_channel: :class:`bool`
            Indicates if the channel is part of the initial channel list.
            This can be useful to ignore channels from the initial channel list
            when you've already assigned them by passing initial_channels to :class:`Shard`.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def start(self) -> None:
        """|coro|

        Method to be overriden in a subclass.

        This method is called when :meth:`Client/Bot.start <twitchio.Client.start>` is called.
        It should be used to start shards, and should wait until they've all exited before returning.
        You can use :meth:`await self.wait_until_exit <wait_until_exit>` to do this easily.
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    async def stop(self) -> None:
        """|coro|
        
        Method to be overriden in a subclass.

        This method is called when :meth:`Client/Bot.stop <twitchio.Client.stop>` is called.
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    async def get_sender_shard(self, channel_name: str) -> Shard:
        """|coro|
        
        Method to be overriden in a subclass.

        This method is called whenever the library needs to know what shard to use to send a message with.
        Unless you have different users logged in on different shards, you can typically return any shard.

        .. note::
            You do not need to have joined a channel's chat to send messages to it.

        Parameters
        -----------
        channel_name: :class:`str`
            The channel to send a message to.
        """
        raise NotImplementedError


class DefaultShardManager(BaseShardManager):
    """
    The default shard manager.
    This will be used by default if no other shard manager is passed to :class:`~twitchio.Client`.

    The documentation for each overriden function below will contain it's implementation for reference purposes.

    .. versionadded:: 3.0

    Attributes
    -----------
    main_shard: :class:`Shard`
        The sole shard in use.
    """
    main_shard: Shard

    async def setup(self, **kwargs) -> None:
        """|coro|
        
        Sets up the :class:`DefaultShardManager`.
        Calls :meth:`TokenHandler.get_irc_token(None) <twitchio.BaseTokenHandler.get_irc_token>` to get a token to log in with.

        The implementation looks like this:

        .. code-block:: python

            _, user = await self.token_handler._client_get_irc_login(self.client, None)
            self.main_shard = self.add_shard("main-shard", user.name)
        
        """
        _, user = await self.token_handler._client_get_irc_login(self.client, None) # type: ignore

        assert user.name
        self.main_shard = self.add_shard("main-shard", user.name)
    
    async def assign_shard(self, channel_name: str, is_initial_channel: bool) -> None:
        """|coro|
        
        Assigns a channel to a shard. 
        Because this implementation only uses one shard, it is quite simple.
        
        The implementation looks like this:

        .. code-block:: python

            if is_initial_channel:
                return
            
            await self.main_shard.add_channels((channel_name,))
        """
        if is_initial_channel:
            return
        
        await self.main_shard.add_channels((channel_name,))
    
    async def start(self) -> None:
        """|coro|
        
        Starts the shard, enabling it to send and receive messages.
        
        The implementation looks like this:

        .. code-block:: python

            await self.main_shard.start(block=True)
        """
        await self.main_shard.start(block=True)
    
    async def stop(self) -> None:
        """|coro|
        
        Stops the shard, closing its connection to twitch.
        
        The implementation looks like this:

        .. code-block:: python

            await self.main_shard.stop()
        """
        await self.main_shard.stop()
    
    async def get_sender_shard(self, channel_name: str) -> Shard:
        """|coro|
        
        Returns the only shard available. Nothing interesting.

        Parameters
        -----------
        channel_name: :class:`str`
            The channel to send a message to.
        """
        return self.main_shard


class DistributedShardManager(BaseShardManager):
    """
    A distributed shard manager.
    This shard manager will distribute channels across multiple shards, allowing for more channels to be read from concurrently.
    This shard manager still uses one user as the login user.

    The documentation for each overriden function can be viewed on GitHub.

    .. versionadded:: 3.0

    The following parameters are passed to :class:`~twitchio.Client`:
    
    Parameters
    -----------
    channels_per_shard: :class:`int`
        The maximum amount of channels per shard. Defaults to 25.
    max_shard_count: :class:`int` | ``None``
        The maxiumum amount of shards that the manager is allowed to create. Defaults to 5.
    initial_shard_count: :class:`int`
        The amount of initial shards that the manager should create and distribute initial channels across. Defaults to 1.


    Attributes
    -----------
    channels_per_shard: :class:`int`
        The amount of channels that can be put on each shard.
    max_shard_count: :class:`int` | ``None``
        The maximum amount of shards that the manager is allowed to create.
    """

    authorized_name: str
    next_shard_id: int

    async def setup(self, **kwargs) -> None:
        """|coro|
        
        Sets up the initial state of the shard manager.
        creates ``initial_shard_count`` shards, and splits the initial channels (if any) into them.
        If more initial channels are provided than the initial shard count can handle, it will create more.

        The implementation of this is quite long, please view it on GitHub.
        """
        self.next_shard_id = 1
        self.channels_per_shard: int = kwargs.get("channels_per_shard", 25)
        self.max_shard_count: int = kwargs.get("max_shard_count", 5)
        initial_shards: int = kwargs.get("initial_shard_count", 1)

        _, user = await self.token_handler._client_get_irc_login(self.client, None) # type: ignore
        assert user.name

        self.authorized_name = user.name

        if self.initial_channels:
            assignable = list(self.initial_channels)
            slice_size = math.floor(len(assignable) / initial_shards)

            if slice_size > self.channels_per_shard: # we need to add more shards to startup
                initial_shards = math.ceil(len(assignable) / self.channels_per_shard)
                if initial_shards > self.max_shard_count:
                    e = RuntimeError("More channels have been added to initial_channels than are allowed by the combination "
                                       "of channels_per_shard and max_shard_count. Consider using larger amounts for these values.")
                    
                    if PY_311:
                        e.add_note(f"TIP: Try passing a larger `max_shard_count` argument to your Client/Bot. Current is {self.max_shard_count}.")
                        e.add_note(f"TIP: Try passing a larger `channels_per_shard` argument to your Client/Bot. Current is {self.channels_per_shard}.")

                    raise e

                slice_size = math.floor(len(assignable) / initial_shards)

            for idx in range(1, initial_shards+1):
                if idx < initial_shards:
                    chnl_slice = assignable[:slice_size]
                    assignable = assignable[slice_size:]
                else:
                    chnl_slice = assignable
                
                self.add_shard(f"initial-shard-{idx}", self.authorized_name, initial_channels=chnl_slice)
        else:
            for idx in range(1, initial_shards+1):
                self.add_shard(f"initial-shard-{idx}", self.authorized_name)

    async def assign_shard(self, channel_name: str, is_initial_channel: bool) -> None:
        """|coro|
        
        Assigns a channel to a shard. 
        To distribute evenly, this method checks all existing shard levels, and finds the one with the least amount of shards.
        If all the shards are at their limits, it will create a new shard instead.
        
        The implementation looks like this:

        .. code-block:: python

            if is_initial_channel:
                return
            
            ideal_shard = min(self.shards.values(), key=lambda shard: len(shard.websocket._channels))
            
            if len(ideal_shard.websocket._channels) >= self.channels_per_shard:
                if len(self.shards) >= self.max_shard_count:
                    raise RuntimeError("All shards are full, and the shard count limit has been reached.")
                
                new_shard_id = f"extended-shard-{self.next_shard_id}"
                self.next_shard_id += 1

                ideal_shard = self.add_shard(new_shard_id, self.authorized_name)
                await ideal_shard.start(block=False)
            
            await ideal_shard.add_channels((channel_name,))
        """
        if is_initial_channel:
            return
        
        ideal_shard = min(self.shards.values(), key=lambda shard: len(shard.websocket._channels))

        if len(ideal_shard.websocket._channels) >= self.channels_per_shard:
            if len(self.shards) >= self.max_shard_count:
                e = RuntimeError("All shards are full, and the shard count limit has been reached.")
                if PY_311:
                    e.add_note(f"TIP: Try passing a larger `max_shard_count` argument to your Client/Bot. Current is {self.max_shard_count}.")
                
                raise e

            new_shard_id = f"extended-shard-{self.next_shard_id}"
            self.next_shard_id += 1

            ideal_shard = self.add_shard(new_shard_id, self.authorized_name)
            await ideal_shard.start(block=False)
        
        await ideal_shard.add_channels((channel_name,))
    
    async def start(self) -> None:
        """|coro|
        
        Starts all shards, enabling them to send and receive messages.
        
        The implementation looks like this:

        .. code-block:: python

            await self.start_all_shards()
            await self.wait_until_exit()
        """
        await self.start_all_shards()
        await self.wait_until_exit()
    
    async def stop(self) -> None:
        """|coro|
        
        Stops all shards, closing their connections to twitch.
        
        The implementation looks like this:

        .. code-block:: python

            await self.stop_all_shards()
        """
        await self.stop_all_shards()
        
    async def get_sender_shard(self, channel_name: str) -> Shard:
        """|coro|
        
        Fetches the first shard available to send from.

        The implementation looks like this:

        .. code-block:: python

            return next(iter(self.shards.values()))
        """
        return next(iter(self.shards.values()))


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
