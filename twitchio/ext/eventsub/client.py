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

import logging
from typing import TYPE_CHECKING, Any, Generic, Awaitable, Type
from typing_extensions import Self

import aiohttp
from twitchio import Client as _BaseClient, PartialUser
from twitchio.http import Route, TokenHandlerT, HTTPHandler

if TYPE_CHECKING:
    from . import models
    from .events import BaseEvent, ChallengeEvent, NotificationEvent, RevocationEvent
    from .transport import BaseTransport
    from .types.payloads import HTTPSubscribeResponse

__all__ = ("Client",)


logger = logging.getLogger("twitchio.ext.eventsub.client")


class Client(Generic[TokenHandlerT]):
    """
    The base EventSub client, which handles incoming eventsub data and dispatches it through its own event system.
    This client is completely standalone from the core TwitchIO :class:`~twitchio.Client`, and can operate without any attached :class:`~twitchio.Client`.
    When operating in standalone mode, a Token Handler is still required to manage token access for HTTP calls.
    To operate Eventsub with a core :class:`twitchio.Client` attached, create this class using :func:`~twitchio.ext.eventsub.client.Client.from_client`.
    """

    __slots__ = ("_transport", "_core_client", "_http")

    def __init__(
        self,
        transport: BaseTransport,
        token_handler: TokenHandlerT,
        proxy: str | None = None,
        proxy_auth: aiohttp.BasicAuth | None = None,
        trace: aiohttp.TraceConfig | None = None,
    ) -> None:
        """
        Creates a Client that can interface with the Eventsub API system.

        Parameters
        -----------
        transport: :class:`~twitchio.ext.eventsub.transport.WebsocketTransport` | :class:`~twitchio.ext.eventsub.transport.WebhookTransport`
            The transport to use to receive notifications.
            For more information on each transport, read the corresponding documentation.
        token_handler: :class:`twitchio.tokens.TokenHandler`
            The token handler to use for requesting tokens during HTTP requests.
            When using the :class:`~twitchio.ext.eventsub.transport.WebsocketTransport`, this **must** have user tokens available for the targets of the subscriptions.
            When using the :class:`~twitchio.ext.eventsub.transport.WebhookTransport`, this **must** have a client token available, as that is what Twitch requires for webhooks.
        proxy: :class:`str` | ``None``
            The optional proxy to use when making requests. This is passed directly to aiohttp.
        proxy_auth: :class:`aiohttp.BasicAuth` | ``None``
            The auth to give to the proxy. This is passed directly to aiohttp.
        trace: :class:`aiohttp.TraceConfig` | ``None``
            Trace information to configure aiohttp. This is passed directly to aiohttp.
        """
        self._transport: BaseTransport = transport
        self._core_client: _BaseClient | None = None
        self._http: HTTPHandler = HTTPHandler(None, token_handler, proxy=proxy, proxy_auth=proxy_auth, trace=trace)

        self._transport._prepare(self)
        # dear anyone who modifies __init__: does from_client need updating to reflect the changes as well?
    
    @classmethod
    def from_client(cls, transport: BaseTransport, client: _BaseClient) -> Self:
        """
        Creates a Client that can interface with the Eventsub API system.
        When created using this method, the client will interact with the core :class:`~twitchio.Client`, using its token handler,
        and additionally dispatching events through its event system (in addition to the standalone events).

        Parameters
        -----------
        transport: :class:`~twitchio.ext.eventsub.transport.WebsocketTransport` | :class:`~twitchio.ext.eventsub.transport.WebhookTransport`
            The transport to use to receive notifications.
            For more information on each transport, read the corresponding documentation.
        client: :class:`twitchio.Client` | :class:`Twitchio.ext.commands.Bot`
            The core client to attach this client to.
        """
        self = cls.__new__(cls)
        self._transport = transport
        self._core_client = client
        self._http = client._http

        self._transport._prepare(self)

        return self
    
    async def start(self) -> None:
        if not self._http._prepared:
            await self._http.prepare()
        
        await self._transport.start()

    async def stop(self) -> None:
        await self._transport.stop()
        
    async def _request(self, route: Route) -> Any:
        return await self._http.request(route)

    async def _handle_event(self, name: str, event: BaseEvent) -> None:
        if self._core_client:
            # TODO: client doesnt have dispatching mechanisms
            ...

        attr = getattr(self, f"event_{name}", None)
        if not attr:
            return

        await attr(event)  # TODO: capture errors and have self-contained error handler

    # subclassable events

    async def event_challenge(self, event: ChallengeEvent) -> None:
        pass

    async def event_revocation(self, event: RevocationEvent) -> None:
        pass

    async def event_notification(self, event: NotificationEvent) -> None:
        pass

    async def event_channel_update(self, event: NotificationEvent[models.ChannelUpdate]) -> None:
        pass

    async def event_channel_follow(self, event: NotificationEvent[models.ChannelFollow]) -> None:
        pass

    async def event_channel_subscribe(self, event: NotificationEvent[models.ChannelSubscribe]) -> None:
        ...
    
    async def event_channel_subscribe_end(self, event: NotificationEvent[models.ChannelSubscribeEnd]) -> None:
        ...
    
    async def event_channel_subscribe_gift(self, event: NotificationEvent[models.ChannelSubscribeGift]) -> None:
        ...
    
    async def event_channel_subscribe_message(self, event: NotificationEvent[models.ChannelSubscribeMessage]) -> None:
        ...

    # subscription stuff

    def _subscribe_with_broadcaster(self, topic: Type[models.AllModels], broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._transport.create_subscription(topic, {"broadcaster_user_id": str(broadcaster.id)}, broadcaster)

    def subscribe_channel_bans(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelBan, broadcaster)

    def subscribe_channel_unbans(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.unban, broadcaster)

    def subscribe_channel_subscriptions(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribe, broadcaster)

    def subscribe_channel_subscription_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribeEnd, broadcaster)

    def subscribe_channel_subscription_gifts(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribeGift, broadcaster)

    def subscribe_channel_subscription_messages(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribeMessage, broadcaster)

    def subscribe_channel_cheers(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelCheer, broadcaster)

    def subscribe_channel_update(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelUpdate, broadcaster)

    def subscribe_channel_follows(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelFollow, broadcaster)

    def subscribe_channel_moderators_add(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.channel_moderator_add, broadcaster)

    def subscribe_channel_moderators_remove(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.channel_moderator_remove, broadcaster)

    def subscribe_channel_goal_begin(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.channel_goal_begin, broadcaster)

    def subscribe_channel_goal_progress(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.channel_goal_progress, broadcaster)

    def subscribe_channel_goal_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.channel_goal_end, broadcaster)

    def subscribe_channel_hypetrain_begin(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.hypetrain_begin, broadcaster)

    def subscribe_channel_hypetrain_progress(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.hypetrain_progress, broadcaster)

    def subscribe_channel_hypetrain_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.hypetrain_end, broadcaster)

    def subscribe_channel_stream_start(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.stream_start, broadcaster)

    def subscribe_channel_stream_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.SubscriptionTypes.stream_end, broadcaster)