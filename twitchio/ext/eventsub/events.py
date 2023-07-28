from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Generic, Literal, Mapping, Protocol, Type, TypeVar, Union

from typing_extensions import Self

from ... import PartialUser
from ...utils import json_loader, parse_timestamp as _parse_timestamp
from .models import AllModels, _event_map

if TYPE_CHECKING:
    from .transport import BaseTransport
    from .types.payloads import (
        AllPayloads,
        Subscription as _SubscriptionPayload,
        WebhookChallenge as _WebhookChallenge,
        WebhookMessage as _WebhookMessage,
        WebsocketMessage as _WebsocketMessage,
        WebsocketMessageMetadata as _WebsocketMessageMetadata,
        WebsocketReconnectMessage as _WebsocketReconnectMessage,
    )

    TransportType = BaseTransport

__all__ = (
    "Subscription",
    "BaseMeta",
    "WebhookMeta",
    "WebsocketMeta",
    "RevocationEvent",
    "ChallengeEvent",
    "NotificationEvent",
    "ReconnectEvent",
    "KeepaliveEvent",
)


class Subscription:
    """
    Subscription info given when twitch fires an event.
    For info on the message itself, check :attr:`~twitchio.ext.eventsub.BaseEvent.meta`

    Attributes
    -----------
    id: :class:`str`
        The ID of the subscription.
    status: :class:`str`
        The status of the subscription.
    type: :class:`str`
        The subscription type. # TODO doc this better
    version: :class:`int`
        The subscription version. This is relatively useless.
    cost: :class:`int`
        The cost of the the subscription towards your total subscription points.
        If the user has authorized your application this is 0.
    condition: dict[str, Any]
        The condition for this subscription to trigger an event. # TODO determine dicts on this.
    created_at: :class:`~datetime.datetime`
        When the subscption was created.
    transport: :class:`~twitchio.ext.eventsub.BaseTransport`
        The transport that dispatched this event.

        .. versionadded:: 3.0
    session_id: :class:`str` | None
        The id of the websocket this subscription is attached to. This is ``None`` when using the Webhook transport.

        .. versionadded:: 3.0
    """

    id: str
    status: str  # TODO: literals?
    type: str
    version: int
    cost: int
    condition: Any  # FIXME check docs on this
    created_at: datetime.datetime
    transport: BaseTransport
    session_id: str | None

    def __init__(self, payload: _SubscriptionPayload, transport: BaseTransport) -> None:  # FIXME: how to genric this
        self.id = payload["id"]
        self.status = payload["status"]
        self.type = payload["type"]
        self.version = int(payload["version"])
        self.cost = payload["cost"]
        self.condition = payload["condition"]
        self.created_at = _parse_timestamp(payload["created_at"])
        self.transport = transport
        self.session_id = payload["transport"].get("session_id")


class BaseMeta(Protocol):
    """
    The metadata associated with the event message.

    Attributes
    -----------
    message_id: :class:`str`
        The unique id of the message.
    message_type: Literal["notification", "challenge", "revocation", "reconnect", "session_keepalive"]
        The type of the message being received.
    signature: :class:`str` | ``None``
        The signature used to verify the message validity when received over the Webhook transport. This is ``None`` when using the Websocket transport.
    message_retry: :class:`int` | None
        How many retry attempts have been made to deliver this event. This is ``None`` when using the Websocket transport.
    timestamp: :class:`~datetime.datetime`
        When this event was created. Could be different than now if the message has failed to deliver via the Webhook transport.

    """

    message_id: str
    message_type: Literal["notification", "challenge", "revocation", "reconnect", "session_keepalive"]
    signature: str | None
    message_retry: int | None
    timestamp: datetime.datetime


class WebsocketMeta(BaseMeta):
    def __init__(self, data: _WebsocketMessageMetadata) -> None:
        self.message_id = data["message_id"]
        self.message_type = data["message_type"]
        self.timestamp = _parse_timestamp(data["message_timestamp"])

        self.signature = None
        self.message_retry = None


class WebhookMeta(BaseMeta):
    signature: str
    message_retry: int

    def __init__(self, hdrs: Mapping[str, str]) -> None:
        self.message_id = hdrs["Twitch-Eventsub-Message-Id"]
        self.message_type = hdrs["Twitch-Eventsub-Message-Type"]  # type: ignore
        self.timestamp = _parse_timestamp(hdrs["witch-Eventsub-Message-Timestamp"])

        self.signature = hdrs["Twitch-Eventsub-Message-Signature"]
        self.message_retry = int(hdrs["Twitch-Eventsub-Message-Retry"])

        self._raw_timestamp: str = hdrs["witch-Eventsub-Message-Timestamp"]


class BaseEvent(Protocol):
    """
    A base event from which other events stem

    Attributes
    -----------
    subscription: :class:`Subscription`
        The subscription that triggered this event.
    meta: :class:`WebhookMeta` | :class:`WebsocketMeta`
        The metadata associated with this event. There are slight differences between the webhook metadata and websocket metadata.
        This was previously known as ``headers``.

        .. versionchanged:: 3.0
    transport: :class:`BaseTransport`
        The transport that received this event.

        .. versionadded:: 3.0
    """

    subscription: Subscription
    meta: BaseMeta
    transport: BaseTransport

    __slots__ = ("subscription", "meta", "transport")

    def __init__(self, transport: BaseTransport) -> None:
        self.transport = transport

    @classmethod
    def from_webhook_event(cls, transport: BaseTransport, payload: str, headers: Mapping[str, str]) -> Self:
        self = cls(transport)
        data: _WebhookMessage | _WebhookChallenge = json_loader(payload)
        self.subscription = Subscription(data["subscription"], transport)
        self.meta = WebhookMeta(headers)
        if "challenge" in data:
            self.prepare(data)
        else:
            self.prepare(data["payload"])
        return self

    @classmethod
    def from_websocket_event(cls, transport: BaseTransport, payload: _WebsocketMessage) -> Self:
        self = cls(transport)
        self.meta = WebsocketMeta(payload["metadata"])

        if "payload" in payload:
            self.subscription = Subscription(payload["payload"]["subscription"], transport)
            self.prepare(payload["payload"]["event"])

        else:
            self.prepare(payload)  # type: ignore

        return self

    def prepare(self, data: dict) -> None:
        ...


class RevocationEvent(BaseEvent):
    """
    Event created when someone revokes access for your app.
    This event has no special attributes, you can determine information about the revoked event via :attr:`~subscription`.
    You can listen to this event via the ``event_eventsub_revocation`` event or via :ref:`subclassing the EventSub client <eventsub_subclass_ref>`.

    Attributes
    -----------
    subscription: :class:`Subscription`
        The subscription that triggered this event.
    meta: :class:`WebhookMeta` | :class:`WebsocketMeta`
        The metadata associated with this event. There are slight differences between the webhook metadata and websocket metadata.
        This was previously known as ``headers``.

        .. versionchanged:: 3.0
    transport: :class:`BaseTransport`
        The transport that received this event.

        .. versionadded:: 3.0
    """

    subscription: Subscription
    meta: BaseMeta
    transport: BaseTransport

    def prepare(self, data: dict) -> None:
        pass


class ChallengeEvent(BaseEvent):
    """
    This event is created to challenge your webhook authenticity (meaning it is only used when using the :class:`~twitchio.ext.eventsub.WebhookTransport` transport).
    These challenges are handled by TwitchIO, so you shouldn't need to deal with these.
    You can listen to this event via the ``event_eventsub_challenge`` event or via :ref:`subclassing the EventSub client <eventsub_subclass_ref>`.


    Attributes
    -----------
    challenge: :class:`str`
        The challenge string given by twitch.
    subscription: :class:`Subscription`
        The subscription that triggered this event.
    meta: :class:`WebhookMeta` | :class:`WebsocketMeta`
        The metadata associated with this event. There are slight differences between the webhook metadata and websocket metadata.
        This was previously known as ``headers``.

        .. versionchanged:: 3.0
    transport: :class:`BaseTransport`
        The transport that received this event.

        .. versionadded:: 3.0
    """

    subscription: Subscription
    meta: BaseMeta
    transport: BaseTransport

    __slots__ = ("challenge",)

    def prepare(self, data: _WebhookChallenge) -> None:
        self.challenge: str = data["challenge"]


D = TypeVar("D", bound=AllModels)


class NotificationEvent(BaseEvent, Generic[D]):
    """
    This event is created when a notification is received from twitch.

    Attributes
    -----------
    data: :ref:`A Model <eventsub_models>`
        The data for this event. This will change depending on the event in question
    subscription: :class:`Subscription`
        The subscription that triggered this event.
    meta: :class:`WebhookMeta` | :class:`WebsocketMeta`
        The metadata associated with this event. There are slight differences between the webhook metadata and websocket metadata.
        This was previously known as ``headers``.

        .. versionchanged:: 3.0
    transport: :class:`BaseTransport`
        The transport that received this event.

        .. versionadded:: 3.0
    """

    subscription: Subscription
    meta: BaseMeta
    transport: BaseTransport
    data: D

    __slots__ = ("data",)

    def prepare(self, data: AllPayloads):
        typ = self.subscription.type
        d = _event_map[typ](self.transport, data)

        self.data = d  # type: ignore


class ReconnectEvent(BaseEvent):
    """
    This event is created when the twitch websocket wants the client to reconnect.
    Reconnecting is automatically handled, this event is simply to inform you of it happening.

    Attributes
    -----------
    reconnect_url: class:`str`
        The URL provided by twitch to reconnect to. This will keep the existing subscriptions intact for us.
    subscription: :class:`Subscription`
        The subscription that triggered this event.
    meta: :class:`WebhookMeta` | :class:`WebsocketMeta`
        The metadata associated with this event. There are slight differences between the webhook metadata and websocket metadata.
        This was previously known as ``headers``.

        .. versionchanged:: 3.0
    transport: :class:`BaseTransport`
        The transport that received this event.

        .. versionadded:: 3.0
    """

    subscription: Subscription
    meta: BaseMeta
    transport: BaseTransport
    reconnect_url: str

    __slots__ = ("reconect_url",)

    def prepare(self, data: _WebsocketReconnectMessage) -> None:
        self.reconect_url = data["payload"]["session"]["reconnect_url"]


class KeepaliveEvent(BaseEvent):
    """
    This event is created to fill space and let you know twitch is still sending you events after a spout of silence.
    Nothing needs to be done.

    Attributes
    -----------
    subscription: :class:`Subscription`
        The subscription that triggered this event.
    meta: :class:`WebhookMeta` | :class:`WebsocketMeta`
        The metadata associated with this event. There are slight differences between the webhook metadata and websocket metadata.
        This was previously known as ``headers``.

        .. versionchanged:: 3.0
    transport: :class:`BaseTransport`
        The transport that received this event.

        .. versionadded:: 3.0
    """

    subscription: Subscription
    meta: BaseMeta
    transport: BaseTransport

    def prepare(self, data: dict) -> None:
        pass
