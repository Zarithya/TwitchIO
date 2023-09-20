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
import inspect
import logging
import sys
import traceback
import uuid
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, Literal, overload

from twitchio.http import HTTPAwaitableAsyncIterator, HTTPHandler

from .channel import Channel
from .chatter import PartialChatter
from .exceptions import HTTPException
from .limiter import IRCRateLimiter
from .message import Message
from .models import *
from .parser import IRCPayload
from .shards import ShardInfo
from .tokens import BaseTokenHandler
from .websocket import Websocket

_initial_channels_T = list[str] | tuple[str] | Callable[[], list[str]] | Coroutine[Any, Any, None] | None

__all__ = ("Client",)

logger = logging.getLogger("twitchio.client")

class Event:
    __slots__ = ("_callback", "event", "cb_uuid")

    def __init__(self, callback: Callable[[Any], Coroutine[Any, Any, None]], event: str, callback_uuid: uuid.UUID) -> None:
        self._callback = callback
        
        self.event = event
        self.cb_uuid = callback_uuid
    
    def __call__(self, arg: Any) -> Coroutine[Any, Any, None]:
        return self._callback(arg)
    
    def __hash__(self) -> int:
        return hash(self.cb_uuid.int)
    
    def __eq__(self, other: object) -> bool:
        return isinstance(other, Event) and other.cb_uuid == self.cb_uuid
    

class Client:
    """THe main Twitch HTTP and IRC Client.

    This client can be used as a standalone to both HTTP and IRC or used together.

    Parameters
    ----------
    token_handler: :class:`~twitchio.BaseTokenHandler`
        Your token handler instance. See ... # TODO doc link to explaining token handlers
    heartbeat: Optional[:class:`float`]
        An optional heartbeat to provide to keep connections over proxies and such alive.
        Defaults to 30.0.
    verified: Optional[:class:`bool`]
        Whether or not your bot is verified or not. Defaults to False.
    join_timeout: Optional[:class:`float`]
        An optional float to use to timeout channel joins. Defaults to 15.0.
    initial_channels: Optional[Union[list[:class:`str`], tuple[:class:`str`], :class:`callable`, :class:`coroutine`]]
        An optional list or tuple of channels to join on bot start. This may be a callable or coroutine,
        but must return a :class:`list` or :class:`tuple`.
    shard_limit: :class:`int`
        The amount of channels per websocket. Defaults to 100 channels per socket.
    cache_size: Optional[:class:`int`]
        The size of the internal channel cache. Defaults to unlimited.
    eventsub: Optional[:class:`~twitchio.ext.EventSubClient`]
        The EventSubClient instance to use with the client to dispatch subscribed webhook events.
    """

    def __init__(
        self,
        token_handler: BaseTokenHandler,
        heartbeat: float | None = 30.0,
        verified: bool | None = False,
        join_timeout: float | None = 15.0,
        initial_channels: _initial_channels_T = None,
        shard_limit: int = 100,
        cache_size: int | None = None,
        **kwargs,
    ):
        self._token_handler: BaseTokenHandler = token_handler._post_init(self)
        self._heartbeat = heartbeat
        self._verified = verified
        self._join_timeout = join_timeout

        self._cache_size = cache_size

        self._shards = {}
        self._shard_limit = shard_limit
        self._initial_channels: _initial_channels_T = initial_channels or []

        self._limiter = IRCRateLimiter(status="verified" if verified else "user", bucket="joins")
        self._http = HTTPHandler(None, self._token_handler, client=self, **kwargs)

        self.loop: asyncio.AbstractEventLoop | None = None
        self._kwargs: dict[str, Any] = kwargs

        self._is_closed = False
        self._has_acquired = False

        self._events: dict[str, set[Event]] = {}

    async def __aenter__(self):
        await self.setup()
        self._has_acquired = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._has_acquired = False
        if not self._is_closed:
            await self.close()
    
    def add_event_listener(self, event_name: str, callback: Callable[[Any], Coroutine[Any, Any, None]]) -> Event:
        """
        Adds an event listener to the Client.
        The event name must not have whitespace, and must not start with ``event_``.

        .. versionchanged:: 3.0
            This is now publicly documented.
        
        Parameters
        -----------
        event_name: :class:`str`
            The event to dispatch this listener for.
        callback: Coroutine
            An async function that takes one argument. It will be called whenever the event is dispatched.
        
        Returns
        --------
            ``Event``
                Not much use anywhere except removing events, which typically won't need to be done manually.
        """
        if " " in event_name or event_name.startswith("event_"):
            raise ValueError("Invalid event name: contains whitespace or starts with 'event_'")
        
        if event_name not in self._events:
            self._events[event_name] = set()
        
        cb_uuid = uuid.uuid4()
        container = Event(callback, event_name, cb_uuid)
        
        try:
            callback._event = container
        except:
            logger.debug("Could not add reference to event back to callback for function %s. This may make removing it difficult.", repr(callback))
        
        self._events[event_name].add(container)

        return container

    def remove_event_listener(self, listener: Event | Callable) -> None:
        """
        Removes an event listener from the Client.
        You must pass an ``Event`` or a function that has been marked as an event (usually with the :meth:`@client.listener <Client.listener>` decorator.)

        .. versionchanged:: 3.0
            This is now publicly documented.
        
        Parameters
        -----------
        listener: ``Event`` | ``Coroutine``
            The listener to remove, or its corresponding ``Event`` container.
        
        """
        if not isinstance(listener, Event):
            try:
                event_ = listener._event
            except AttributeError:
                raise ValueError("The given function is not an event.")

        else:
            event_ = listener
        
        name = event_.event
        if name not in self._events:
            raise ValueError("The event is registered to a nonexistant event name.")
        
        try:
            self._events[name].remove(event_)
        except KeyError as e:
            raise ValueError("The event is not registered.") from e
    
    @overload
    def listener(self, name_or_function: Callable[[Any], Coroutine[Any, Any, None]]) -> Event:
        ...
    
    @overload
    def listener(self, name_or_function: str) -> Callable[[Callable[[Any], Coroutine[Any, Any, None]]], Event]:
        ...
    
    def listener(self, name_or_function: str | Callable[[Any], Coroutine[Any, Any, None]]) -> Callable[[Callable[[Any], Coroutine[Any, Any, None]]], Event] | Event:
        """
        A decorator for adding event listeners to the Client. This can be used in two different ways.

        1)
        
        .. code-block:: python

            @client.listener
            async def event_message(message: twitchio.Message) -> None:
                ...
        
        Or, 2)

        .. code-block:: python

            @client.listener("message") # or "event_message"
            async def this_is_a_message_listener(message: twitchio.Message) -> None:
                ...
        
        .. versionchanged:: 3.0
            This can now be used without the name in the decorator.
        
        Returns
        --------
            ``Event``
                Turns the function into an ``Event``. The function can still be called like normal, but has some special properties for dispatching events to it.
        """
        if callable(name_or_function):
            name = name_or_function.__name__.removeprefix("event_")
            event = self.add_event_listener(name, name_or_function)
            return event

        else:
            def wraps(fn: Callable[[Any], Coroutine[Any, Any, None]]) -> Event:
                event = self.add_event_listener(name_or_function.removeprefix("event_"), fn)
                return event

            return wraps

    async def _shard(self):
        if inspect.iscoroutinefunction(self._initial_channels):
            channels = await self._initial_channels()

        elif callable(self._initial_channels):
            channels = self._initial_channels()

        elif isinstance(self._initial_channels, (list, tuple)):
            channels = self._initial_channels
        else:
            raise TypeError("initial_channels must be a list, tuple, callable or coroutine returning a list or tuple.")

        if not isinstance(channels, (list, tuple)):
            raise TypeError("initial_channels must return a list or tuple of str.")

        chunked = [channels[x : x + self._shard_limit] for x in range(0, len(channels), self._shard_limit)]

        for index, chunk in enumerate(chunked, 1):
            self._shards[index] = ShardInfo(
                number=index,
                channels=channels,
                websocket=Websocket(
                    token_handler=self._token_handler,
                    client=self,
                    limiter=self._limiter,
                    shard_index=index,
                    heartbeat=self._heartbeat,
                    join_timeout=self._join_timeout,
                    initial_channels=chunk,  # type: ignore
                    cache_size=self._cache_size,
                    **self._kwargs,
                ),
            )

    def run(self) -> None:
        """
        A blocking call that starts and connects the bot to IRC.

        This methods abstracts away starting and cleaning up for you.

        .. warning::

            You should not use this method unless you are connecting to IRC.

        .. note::

            Since this method is blocking it should be the last thing to be called.
            Anything under it will only execute after this method has completed.

        .. note::

            If you want to take more control over cleanup, see :meth:`close`.
        """

        async def _runner():
            try:
                async with self:
                    await self.start()
            except KeyboardInterrupt:
                await self.close()

        asyncio.run(_runner())

    async def start(self) -> None:
        """|coro|

        This method connects to twitch's IRC servers, and prepares to handle incoming messages.
        This method will not return until all the IRC shards have been closed
        """
        if not self._has_acquired:
            raise RuntimeError(
                "You must first enter an async context by calling `async with client:`"
            )  # TODO need better error

        await self.setup()
        await self._shard()

        shard_tasks = [asyncio.create_task(shard._websocket._connect()) for shard in self._shards.values()]

        await asyncio.wait(shard_tasks)

    async def close(self) -> None:
        for shard in self._shards.values():
            await shard._websocket.close()

        await self._http.cleanup()

        self._is_closed = True

    @property
    def shards(self) -> dict[int, ShardInfo]:
        """A dict of shard number to :class:`~twitchio.ShardInfo`"""
        return self._shards

    @property
    def nick(self) -> str | None:
        """
        The bots nickname.

        This may be None if a shard has not become ready, or you have entered invalid credentials.
        """
        return self._shards[1]._websocket.nick

    nickname = nick

    def get_channel(self, name: str, /) -> Channel | None:
        """
        Method which returns a channel from cache if it exits.

        Could be ``None`` if the channel is not in cache.

        Parameters
        ----------
        name: :class:`str`
            The name of the channel to search cache for.

        Returns
        -------
            :class:`~twitchio.Channel` | ``None``
        """
        name = name.strip("#").lower()

        channel = None

        for shard in self._shards.values():
            channel = shard._websocket._channel_cache.get(name, default=None)

            if channel:
                break

        return channel

    def get_message(self, id_: str, /) -> Message | None:
        """
        Method which returns a message from cache if it exists.

        Could be ``None`` if the message is not in cache.

        Parameters
        ----------
        id_: :class:`str`
            The message ID to search cache for.

        Returns
        -------
            :class:`~twitchio.Message` | ``None``
        """
        message = None

        for shard in self._shards.values():
            message = shard._websocket._message_cache.get(id_, default=None)

            if message:
                break

        return message

    def get_partial_user(self, user_id: int | str, user_name: str | None) -> PartialUser:
        """
        Creates a PartialUser with the provided user_id and user_name.

        Parameters
        -----------
        user_id: :class:`int` | :class:`str`
            The numeric ID of the user.
        user_name: :class:`str`
            The name of the user.
        
        Returns
        --------
            :class:`~twitchio.PartialUser`
        """

        return PartialUser(self._http, user_id, user_name)

    def fetch_users(
        self, names: list[str] | None = None, ids: list[int] | None = None, target: BaseUser | None = None
    ) -> HTTPAwaitableAsyncIterator[User]:
        """|aai|

        Fetches users from twitch. You can provide any combination of up to 100 names and ids, but you must pass at least 1.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`
        
        Parameters
        -----------
        names: Optional[list[:class:`str`]]
            A list of usernames.
        ids: Optional[list[Union[:class:`str`, :class:`int`]]
            A list of IDs.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.User`]
        """
        if not names and not ids:
            raise ValueError("No names or ids passed to fetch_users")

        data: HTTPAwaitableAsyncIterator[User] = self._http.get_users(ids=ids, logins=names, target=target)
        data.set_adapter(lambda http, data: User(http, data))

        return data

    async def fetch_user(self, name: str | None = None, id: int | None = None, target: BaseUser | None = None) -> User | None:
        """|coro|

        Fetches a user from twitch. This is the same as :meth:`~Client.fetch_users`, but only returns one :class:`~twitchio.User`, instead of a list.
        You may only provide either name or id, not both.

        .. versionchanged:: 3.0
            Now returns ``User | None`` instead of raising IndexError when the user isn't found.
        
        Parameters
        -----------
        name: Optional[:class:`str`]
            A username.
        id: Optional[:class:`int`]
            A user ID.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.User`
        """
        if not name and not id:
            raise ValueError("Expected a name or id")

        if name and id:
            raise ValueError("Expected a name or id, got nothing")

        data: HTTPAwaitableAsyncIterator[User] = self._http.get_users(
            ids=[id] if id else None, logins=[name] if name else None, target=target
        )
        data.set_adapter(lambda http, data: User(http, data))
        resp = await data

        return resp[0] if resp else None

    async def fetch_cheermotes(self, user_id: int | None = None, target: BaseUser | None = None) -> list[CheerEmote]:
        """|coro|


        Fetches cheermotes from the twitch API.

        Parameters
        -----------
        user_id: Optional[:class:`int`]
            The channel id to fetch from.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.

        Returns
        --------
            list[:class:`twitchio.CheerEmote`]
        """
        data = await self._http.get_cheermotes(str(user_id) if user_id else None, target=target)
        return [CheerEmote(self._http, x) for x in data["data"]]

    def search_channels(self, query: str, *, live_only=False, target: BaseUser | None = None) -> HTTPAwaitableAsyncIterator[SearchUser]:
        """|coro|

        Searches channels for the given query.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`
        
        Parameters
        -----------
        query: :class:`str`
            The query to search for.
        live_only: :class:`bool`
            Only search live channels. Defaults to ``False``.

        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.SearchUser`]
        """

        data: HTTPAwaitableAsyncIterator[SearchUser] = self._http.get_search_channels(
            query, live=live_only, target=target
        )
        data.set_adapter(lambda http, data: SearchUser(http, data))

        return data

    def search_categories(self, query: str, target: BaseUser | None = None) -> HTTPAwaitableAsyncIterator[Game]:
        """|aai|

        Searches Twitch categories.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`
        
        Parameters
        -----------
        query: :class:`str`
            The query to search for.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.Game`]
        """

        data: HTTPAwaitableAsyncIterator[Game] = self._http.get_search_categories(query=query, target=target)
        data.set_adapter(lambda http, data: Game(http, data))

        return data

    async def fetch_channel_info(self, broadcaster_ids: list[int], target: BaseUser | None = None) -> list[ChannelInfo]:
        """|coro|

        Retrieve channel information from the API.

        Parameters
        -----------
        broadcaster_ids: list[str]
            A list of channel IDs to request from API. Returns empty list if no channel was found.
            You may specify a maximum of 100 IDs.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.

        Returns
        --------
            list[:class:`twitchio.ChannelInfo`]
        """

        try:
            data = await self._http.get_channels(broadcaster_ids=broadcaster_ids, target=target)

            return [ChannelInfo(self._http, c) for c in data["data"]]

        except HTTPException as e:
            raise HTTPException("Incorrect channel ID provided") from e

    def fetch_clips(self, ids: list[str], game_id: str | None = None, target: BaseUser | None = None) -> HTTPAwaitableAsyncIterator[Clip]:
        """|aai|

        Fetches clips by clip id or game id.
        To fetch clips by user id, use :meth:`twitchio.PartialUser.fetch_clips`.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`
        
        Parameters
        -----------
        ids: list[:class:`str`]
            A list of clip ids.
        game_id: :class:`str`
            A game id.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.Clip`]
        """

        data: HTTPAwaitableAsyncIterator[Clip] = self._http.get_clips(ids=ids, game_id=game_id, target=target)
        data.set_adapter(lambda http, data: Clip(http, data))

        return data

    def fetch_videos(
        self,
        ids: list[int] | None = None,
        game_id: int | None = None,
        period: Literal["all", "day", "week", "month"] = "all",
        sort: Literal["time", "trending", "views"] = "time",
        type: Literal["all", "upload", "archive", "highlight"] = "all",
        language: str | None = None,
        target: BaseUser | None = None,
    ) -> HTTPAwaitableAsyncIterator[Video]:
        """|aai|

        Fetches videos by id or game id.
        To fetch videos by user id, use :meth:`twitchio.PartialUser.fetch_videos`.

        .. versionchanged:: 3.0
            Parameters now use ``Literal`` instead of ``str | None`` where applicable. Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`.

        Parameters
        -----------
        ids: Optional[list[:class:`int`]]
            A list of video ids up to 100.
        game_id: Optional[:class:`int`]
            A game to fetch videos from. Limit 1.
        period: Optional[:class:`str`]
            The period for which to fetch videos. Valid values are ``all``, ``day``, ``week``, ``month``. Defaults to ``all``.
            Cannot be used when video id(s) are passed.
        sort: Optional[:class:`str`]
            Sort orders of the videos. Valid values are ``time``, ``trending``, ``views``, Defaults to ``time``.
            Cannot be used when video id(s) are passed.
        type: Optional[:class:`str`]
            Type of the videos to fetch. Valid values are ``all``, ``upload``, ``archive``, ``highlight``. Defaults to ``all``.
            Cannot be used when video id(s) are passed.
        language: Optional[:class:`str`]
            Language of the videos to fetch. Must be an `ISO-639-1 <https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes>`_ two letter code.
            Cannot be used when video id(s) are passed.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.Video`]
        """

        data: HTTPAwaitableAsyncIterator[Video] = self._http.get_videos(
            ids=ids, game_id=str(game_id), period=period, sort=sort, type=type, language=language, target=target
        )
        data.set_adapter(lambda http, data: Video(http, data))

        return data

    async def fetch_chatter_colors(self, user_ids: list[int], target: BaseUser | None = None) -> list[ChatterColor]:
        """|coro|

        Fetches the color of a chatter.

        .. versionchanged:: 3.0
            Removed the ``token`` parameter. Added the ``target`` parameter.
        
        Parameters
        -----------
        user_ids: list[:class:`int`]
            List of user ids to fetch the colors for.
        target: Optional[:class:`~twitchio.BaseUser`]
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.

        Returns
        --------
            list[:class:`twitchio.ChatterColor`]
        """
        data = await self._http.get_user_chat_color(user_ids, target)
        return [ChatterColor(self._http, x) for x in data["data"]]
    
    async def update_chatter_color(self, target: BaseUser, color: Literal["blue", "blue_violet", "cadet_blue", "chocolate", "coral", "dodger_blue", "firebrick", "golden_rod", "green", "hot_pink", "orange_red", "red", "sea_green", "spring_green", "yellow_green"] | str) -> None:
        """|coro|

        Updates the color of the specified user in the specified channel/broadcaster's chat.

        Requires an OAuth token with the ``user:manage:chat_color`` scope.

        .. versionchanged:: 3.0
            Removed ``token`` & ``user_id`` parameters. Added literals to color parameter.
        
        Parameters
        -----------
        target: :class:`~twitchio.BaseUser`
            The user to change the chat color for.
        color: :class:`str`
            All users may use any of the named colors:
            - blue
            - blue_violet
            - cadet_blue
            - chocolate
            - coral
            - dodger_blue
            - firebrick
            - golden_rod
            - green
            - hot_pink
            - orange_red
            - red
            - sea_green
            - spring_green
            - yellow_green

            Turbo and Prime users may specify a named color or a Hex color code like ``#9146FF``.
        
        Raises
        -------
            :err:`~twitchio.BadRequest`
                The color parameter was either not valid, or you provided a hex value without being a prime or turbo member.
        """

        # "mom can we have urlencoding"
        # "we have urlencoding at home"
        color = color.replace("#", "%23")

        await self._http.put_user_chat_color(target=target, color=color)

    def fetch_games(
        self,
        ids: list[int] | None = None,
        names: list[str] | None = None,
        igdb_ids: list[int] | None = None,
        target: BaseUser | None = None,
    ) -> HTTPAwaitableAsyncIterator[Game]:
        """|aai|

        Fetches games by id, name or IGDB id.
        At least one id or name must be provided.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`
        
        Parameters
        -----------
        ids: list[:class:`int`] | ``None``
            An optional list of game ids.
        names: list[:class:`str`] | ``None``
            An optional list of game names.
        igdb_ids: list[:class:`int`] | ``None``
            An optional list of IGDB ids.
        target: :class:`~twitchio.BaseUser` | ``None``
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.Game`]
        """

        data: HTTPAwaitableAsyncIterator[Game] = self._http.get_games(
            game_ids=ids, game_names=names, igdb_ids=igdb_ids, target=target
        )
        data.set_adapter(lambda http, data: Game(http, data))

        return data

    def fetch_streams(
        self,
        user_ids: list[int] | None = None,
        game_ids: list[int] | None = None,
        user_logins: list[str] | None = None,
        languages: list[str] | None = None,
        type: Literal["all", "live"] = "all",
        target: BaseUser | None = None,
    ) -> HTTPAwaitableAsyncIterator[Stream]:
        """|aai|

        Fetches live streams from the helix API.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`.
        
        Parameters
        -----------
        user_ids: Optional[list[:class:`int`]]
            user ids of people whose streams to fetch
        game_ids: Optional[list[:class:`int`]]
            game ids of streams to fetch
        user_logins: Optional[list[:class:`str`]]
            user login names of people whose streams to fetch
        languages: Optional[list[:class:`str`]]
            language for the stream(s). ISO 639-1 or two letter code for supported stream language
        type: Literal["all", "live"]
            The type of stream to fetch. Defaults to "all".
        target: :class:`~twitchio.BaseUser` | ``None``
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.Stream`]
        """

        data: HTTPAwaitableAsyncIterator[Stream] = self._http.get_streams(
            game_ids=game_ids,
            user_ids=user_ids,
            user_logins=user_logins,
            languages=languages,
            type=type,
            target=target,
        )
        data.set_adapter(lambda http, data: Stream(http, data))

        return data

    def fetch_top_games(self, target: BaseUser | None = None) -> HTTPAwaitableAsyncIterator[Game]:
        """|aai|

        Fetches the top streamed games from the api.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`. Added the ``target`` parameter.
        
        Parameters
        ----------
        target: :class:`~twitchio.BaseUser` | ``None``
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        
        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.Game`]
        """
        data: HTTPAwaitableAsyncIterator[Game] = self._http.get_top_games(target=target)
        data.set_adapter(lambda http, data: Game(http, data))

        return data

    def fetch_tags(self, ids: list[str] | None = None, target: BaseUser | None = None) -> HTTPAwaitableAsyncIterator[Tag]:
        """|aai|

        Fetches stream tags.

        .. versionchanged:: 3.0
            Now returns an :class:`AAI <twitchio.HTTPAwaitableAsyncIterator>`. Added the ``target`` parameter.
        
        Parameters
        -----------
        ids: list[:class:`str`] | ``None``
            The ids of the tags to fetch.
        target: :class:`~twitchio.BaseUser` | ``None``
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.

        Returns
        --------
            :class:`~twitchio.HTTPAwaitableAsyncIterator`[:class:`~twitchio.Tag`]
        """

        data: HTTPAwaitableAsyncIterator[Tag] = self._http.get_stream_tags(tag_ids=ids, target=target)
        data.set_adapter(lambda http, data: Tag(http, data))

        return data

    async def fetch_team(
        self, team_name: str | None = None, team_id: int | None = None, target: BaseUser | None = None
    ) -> Team:
        """|coro|

        Fetches information for a specific Twitch Team. You must provide one of ``name`` or ``id``.

        .. versionchanged:: 3.0
            Added the ``target`` parameter.
        
        Parameters
        -----------
        name: :class:`str` | ``None``
            Team name to fetch.
        id: :class:`int` | ``None``
            Team id to fetch.
        target: :class:`~twitchio.BaseUser` | ``None``
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.

        Returns
        --------
            :class:`twitchio.Team`
        """

        data = await self._http.get_teams(
            team_name=team_name,
            team_id=team_id,
            target=target,
        )
        return Team(self._http, data["data"][0])

    async def delete_videos(self, target: BaseUser, ids: list[int | Video]) -> list[int]:
        """|coro|

        Delete videos from the api. Returns the video ids that were successfully deleted.

        Requires an OAuth token with the ``channel:manage:videos`` scope.

        .. versionchanged:: 3.0
            Removed the ``token`` parameter. Added the ``target` parameter.
        
        Parameters
        -----------
        target: :class:`~twitchio.BaseUser`
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.
        ids: list[:class:`int`]
            A list of video ids from the channel of the oauth token to delete.

        Returns
        --------
            list[:class:`int`]
        """
        converted = tuple(x.id if isinstance(x, Video) else x for x in ids)

        resp = []
        for chunk in [converted[x : x + 4] for x in range(0, len(converted), 4)]:
            resp.append(await self._http.delete_videos(target, chunk))

        return resp

    async def fetch_global_chat_badges(self, target: BaseUser | None = None) -> list[ChatBadge]:
        """|coro|

        Fetches Twitch's list of chat badges, which users may use in any channel's chat room.

        Parameters
        -----------
        target: :class:`~twitchio.BaseUser` | ``None``
            The target of this HTTP call. Passing a user will tell the library to put this call under the authorized token for that user, if one exists in your token handler.

        Returns
        --------
            list[:class:`~twitchio.ChatBadges`]
        """
        data = await self._http.get_global_chat_badges(target=target)
        return [ChatBadge(x) for x in data["data"]]

    async def fetch_content_classification_labels(self, locale: str | None = None):
        """|coro|

        Fetches information about Twitch content classification labels.

        Parameters
        -----------
        locale: Optional[:class:`str`]
            Locale for the Content Classification Labels.

        Returns
        --------
        List[:class:`twitchio.ContentClassificationLabel`]
        """
        locale = "en-US" if locale is None else locale
        data = await self._http.get_content_classification_labels(locale)
        return [ContentClassificationLabel(x) for x in data]

    async def event_shard_ready(self, number: int) -> None:
        """|coro|

        Event fired when a shard becomes ready.

        Parameters
        ----------
        number: :class:`int`
            The shard number identifier.

        Returns
        -------
        None
        """
        pass

    async def event_ready(self) -> None:
        """|coro|

        Event fired when the bot has completed startup.
        This includes all shards being ready.

        Returns
        -------
        None
        """
        pass

    async def event_error(self, error: Exception) -> None:
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    async def event_raw_data(self, data: str) -> None:
        """|coro|

        Event fired with the raw data received, unparsed, by Twitch.

        Parameters
        ----------
        data: :class:`str`
            The data received from Twitch.

        Returns
        -------
        None
        """
        pass

    async def event_raw_payload(self, payload: IRCPayload) -> None:
        """|coro|

        Event fired with the parsed IRC payload object.

        Parameters
        ----------
        payload: :class:`~twitchio.IRCPayload`
            The parsed IRC payload from Twitch.

        Returns
        -------
        None
        """
        pass

    async def event_message(self, message: Message) -> None:
        """|coro|

        Event fired when receiving a message in a joined channel.

        Parameters
        ----------
        message: :class:`~twitchio.Message`
            The message received via Twitch.

        Returns
        -------
        None
        """
        pass

    async def event_join(self, channel: Channel, chatter: PartialChatter) -> None:
        """|coro|

        Event fired when a JOIN is received via Twitch.

        Parameters
        ----------
        channel: :class:`~twitchio.Channel`
            ...
        chatter: :class:`~twitchio.PartialChatter`
            ...
        """

    async def event_part(self, channel: Channel | None, chatter: PartialChatter) -> None:
        """|coro|

        Event fired when a PART is received via Twitch.

        Parameters
        ----------
        channel: Optional[:class:`~twitchio.Channel`]
            ... Could be None if the channel is not in your cache.
        chatter: :class:`~twitchio.PartialChatter`
            ...
        """

    async def setup(self) -> None:
        """|coro|

        Method called before the Client has logged in to Twitch, used for asynchronous setup.

        Useful for setting up state, like databases, before the client has logged in.

        .. versionadded:: 3.0
        """
        pass
