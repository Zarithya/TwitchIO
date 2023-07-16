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
from typing import TYPE_CHECKING, Any, Awaitable, Generic, Type

import aiohttp
from typing_extensions import Self

from twitchio import Client as _BaseClient, PartialUser, utils
from twitchio.http import HTTPHandler, Route, TokenHandlerT

from . import models

if TYPE_CHECKING:
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
        """
        Starts the Eventsub Client, which will initialize the underlying transport and subscribe/listen to events.
        """
        if not self._http._prepared:
            await self._http.prepare()

        await self._transport.start()

    async def stop(self) -> None:
        """
        Stops the Eventsub Client, which tells the underlying transport to stop listening for events, and clean up after itself.

        .. note::
            The client cannot be restarted once it has been stopped.

        """
        await self._transport.stop()

        if not self._core_client:
            await self._http.cleanup()

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
        ...

    async def event_revocation(self, event: RevocationEvent) -> None:
        ...

    async def event_notification(self, event: NotificationEvent) -> None:
        ...

    async def event_channel_update(self, event: NotificationEvent[models.ChannelUpdate]) -> None:
        ...

    async def event_channel_follow(self, event: NotificationEvent[models.ChannelFollow]) -> None:
        ...

    async def event_channel_subscribe(self, event: NotificationEvent[models.ChannelSubscribe]) -> None:
        ...

    async def event_channel_subscribe_end(self, event: NotificationEvent[models.ChannelSubscribeEnd]) -> None:
        ...

    async def event_channel_subscribe_gift(self, event: NotificationEvent[models.ChannelSubscribeGift]) -> None:
        ...

    async def event_channel_subscribe_message(self, event: NotificationEvent[models.ChannelSubscribeMessage]) -> None:
        ...

    async def event_channel_cheer(self, event: NotificationEvent[models.ChannelCheer]) -> None:
        ...

    async def event_channel_ban(self, event: NotificationEvent[models.ChannelBan]) -> None:
        ...

    async def event_channel_unban(self, event: NotificationEvent[models.ChannelUnban]) -> None:
        ...

    async def event_channel_goal_begin(self, event: NotificationEvent[models.ChannelGoalBegin]) -> None:
        ...

    async def event_channel_goal_progress(self, event: NotificationEvent[models.ChannelGoalProgress]) -> None:
        ...

    async def event_channel_goal_end(self, event: NotificationEvent[models.ChannelGoalEnd]) -> None:
        ...

    async def event_channel_raid(self, event: NotificationEvent[models.ChannelRaid]) -> None:
        ...

    async def event_channel_moderator_add(self, event: NotificationEvent[models.ChannelModeratorAdd]) -> None:
        ...

    async def event_channel_moderator_remove(self, event: NotificationEvent[models.ChannelModeratorRemove]) -> None:
        ...

    async def event_channel_poll_start(self, event: NotificationEvent[models.ChannelPollBegin]) -> None:
        ...

    async def event_channel_poll_progress(self, event: NotificationEvent[models.ChannelPollProgress]) -> None:
        ...

    async def event_channel_poll_end(self, event: NotificationEvent[models.ChannelPollEnd]) -> None:
        ...

    async def event_channel_reward_add(self, event: NotificationEvent[models.ChannelCustomRewardAdd]) -> None:
        ...

    async def event_channel_reward_update(self, event: NotificationEvent[models.ChannelCustomRewardUpdate]) -> None:
        ...

    async def event_channel_reward_remove(self, event: NotificationEvent[models.ChannelCustomRewardRemove]) -> None:
        ...

    async def event_channel_reward_redemption(
        self, event: NotificationEvent[models.ChannelCustomRewardRedemptionAdd]
    ) -> None:
        ...

    async def event_channel_reward_redemption_update(
        self, event: NotificationEvent[models.ChannelCustomRewardRedemptionUpdate]
    ) -> None:
        ...

    async def event_channel_shoutout_create(self, event: NotificationEvent[models.ChannelShoutoutCreate]) -> None:
        ...

    async def event_channel_shoutout_receive(self, event: NotificationEvent[models.ChannelShoutoutReceive]) -> None:
        ...

    async def event_stream_online(self, event: NotificationEvent[models.StreamOnline]) -> None:
        ...

    async def event_stream_offline(self, event: NotificationEvent[models.StreamOffline]) -> None:
        ...

    # subscription stuff

    def _subscribe_with_broadcaster(
        self, topic: Type[models.AllModels], broadcaster: PartialUser
    ) -> Awaitable[HTTPSubscribeResponse]:
        return self._transport.create_subscription(topic, {"broadcaster_user_id": str(broadcaster.id)}, broadcaster)

    def _subscribe_with_moderator(
        self, topic: Type[models.AllModels], broadcaster: PartialUser, moderator: PartialUser
    ) -> Awaitable[HTTPSubscribeResponse]:
        return self._transport.create_subscription(
            topic, {"broadcaster_user_id": str(broadcaster.id), "moderator_user_id": str(moderator.id)}, moderator
        )

    def subscribe_channel_bans(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        """
        Parameters
        -----------
        broadcaster: :class:`~twitchio.PartialUser`
            The channel to for this subscription to target. This user must have authenticated your app.

        Returns
        --------
        :class:`dict` The response from Twitch.
        keys:
        - data: :class:`list`[Subscription dict] - The subscription that was created.
        - total: :class:`int` - The total subscriptions created.
        - total_cost: :class:`int` - The sum of the cost of existing subscriptions.
        - max_total_cost: :class:`int` - The maximum allowed cost.
        """
        return self._subscribe_with_broadcaster(models.ChannelBan, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_unbans(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelUnban, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_subscriptions(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribe, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_subscription_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribeEnd, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_subscription_gifts(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribeGift, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_subscription_messages(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelSubscribeMessage, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_cheers(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelCheer, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_update(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelUpdate, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_follows(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelFollow, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_moderators_add(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelModeratorAdd, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_moderators_remove(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelModeratorRemove, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_goal_begin(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelGoalBegin, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_goal_progress(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelGoalProgress, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_goal_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelGoalEnd, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_hypetrain_begin(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelHypeTrainBegin, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_hypetrain_progress(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelHypeTrainProgress, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_hypetrain_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelHypeTrainEnd, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_stream_start(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.StreamOnline, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_stream_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.StreamOffline, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_poll_begin(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelPollBegin, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_poll_progress(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelPollProgress, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_poll_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelPollEnd, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_prediction_begin(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelPredictionBegin, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_prediction_progress(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelPredictionProgress, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_prediction_lock(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelPredictionLock, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_prediction_end(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelPredictionEnd, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_reward_add(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelCustomRewardAdd, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_reward_update(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelCustomRewardUpdate, broadcaster)

    @utils.copy_doc(subscribe_channel_bans)
    def subscribe_channel_reward_remove(self, broadcaster: PartialUser) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_broadcaster(models.ChannelCustomRewardRemove, broadcaster)

    def subscribe_channel_reward_redeem(
        self, broadcaster: PartialUser, moderator: PartialUser
    ) -> Awaitable[HTTPSubscribeResponse]:
        """
        Parameters
        -----------
        broadcaster: :class:`~twitchio.PartialUser`
            The channel to for this subscription to target.
        moderator: :class:`~twitchio.PartialUser`
            The moderator that is authorizing the action. This user must have authenticated your app.

        Returns
        --------
        :class:`dict` The response from Twitch.
        keys:
        - data: :class:`list`[Subscription dict] - The subscription that was created.
        - total: :class:`int` - The total subscriptions created.
        - total_cost: :class:`int` - The sum of the cost of existing subscriptions.
        - max_total_cost: :class:`int` - The maximum allowed cost.
        """
        return self._subscribe_with_moderator(models.ChannelCustomRewardRedemptionAdd, broadcaster, moderator)

    @utils.copy_doc(subscribe_channel_reward_redeem)
    def subscribe_channel_reward_redeem_update(
        self, broadcaster: PartialUser, moderator: PartialUser
    ) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_moderator(models.ChannelCustomRewardRedemptionUpdate, broadcaster, moderator)

    @utils.copy_doc(subscribe_channel_reward_redeem)
    def subscribe_channel_shoutout_create(
        self, broadcaster: PartialUser, moderator: PartialUser
    ) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_moderator(models.ChannelShoutoutCreate, broadcaster, moderator)

    @utils.copy_doc(subscribe_channel_reward_redeem)
    def subscribe_channel_shoutout_receive(
        self, broadcaster: PartialUser, moderator: PartialUser
    ) -> Awaitable[HTTPSubscribeResponse]:
        return self._subscribe_with_moderator(models.ChannelShoutoutReceive, broadcaster, moderator)
