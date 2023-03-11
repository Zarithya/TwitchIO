from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Mapping, Protocol, Type, Union

from twitchio import PartialUser
from twitchio.utils import parse_timestamp

if TYPE_CHECKING:
    import datetime

    from .transport import BaseTransport
    from .types.payloads import (
        ChannelBan as ChannelBanPayload,
        ChannelCheer as ChannelCheerPayload,
        ChannelFollow as ChannelFollowPayload,
        ChannelGoalBeginProgress as ChannelGoalBeginProgressPayload,
        ChannelGoalEnd as ChannelGoalEndPayload,
        ChannelHypeTrain_Contributor as ChannelHypeTrain_ContributorPayload,
        ChannelHypeTrainBeginProgress as ChannelHypeTrainBeginProgressPayload,
        ChannelHypeTrainEnd as ChannelHypeTrainEndPayload,
        ChannelModeratorAdd as ChannelModeratorAddPayload,
        ChannelModeratorRemove as ChannelModeratorRemovePayload,
        ChannelRaid as ChannelRaidPayload,
        ChannelSubscribe as ChannelSubscribePayload,
        ChannelSubscriptionEnd as ChannelSubscribeEndPayload,
        ChannelSubscriptionGift as ChannelSubscriptionGiftPayload,
        ChannelSubscriptionMessage as ChannelSubscriptionMessagePayload,
        ChannelUnban as ChannelUnbanPayload,
        ChannelUpdate as ChannelUpdatePayload,
        Images as ImagePayload,
        StreamOffline as StreamOfflinePayload,
        StreamOnline as StreamOnlinePayload,
        UserAuthorizationGrant as UserAuthorizationGrantPayload,
        UserAuthorizationRevoke as UserAuthorizationRevokePayload,
        UserUpdate as UserUpdatePayload,
    )

__all__ = (
    "ImageLinks",
    "EventData",
    "ChannelUpdate",
    "ChannelFollow",
    "ChannelGoalBegin",
    "ChannelGoalEnd",
    "ChannelGoalProgress",
    "ChannelSubscribe",
    "ChannelSubscribeEnd",
    "ChannelSubscribeGift",
    "ChannelSubscribeMessage",
    "ChannelCheer",
    "ChannelBan",
    "ChannelUnban",
    "ChannelRaid",
    "ChannelModeratorAdd",
    "ChannelModeratorRemove",
    "StreamOnline",
    "StreamOffline",
    "UserAuthorizationGrant",
    "UserAuthorizationRevoke",
    "UserUpdate",
)


def _transform_user(transport: BaseTransport, prefix: str, data: Mapping[str, Any]) -> PartialUser:
    ...


class ImageLinks:
    """
    Provides URLS for various image locations.

    .. versionadded:: 3.0

    Attributes
    ------------
    size_1x: :class:`str`
        The 1x size provided by twitch.
    size_2x: :class:`str`
        The 2x size provided by twitch.
    size_4x: :class:`str`
        The 4x size provided by twitch.
    """

    __slots__ = ("size_1x", "size_2x", "size_4x")

    def __init__(self, payload: ImagePayload) -> None:
        self.size_1x: str = payload["url_1x"]
        self.size_2x: str = payload["url_2x"]
        self.size_4x: str = payload["url_4x"]


class EventData(Protocol):
    __slots__ = ()
    _dispatches_as: str
    _required_scopes: tuple[str] | None  # any of the scopes can be used, they're not all required
    _version: int
    _event: str

    def __init__(self, transport: BaseTransport, payload: Any) -> None:
        ...


class ChannelUpdate(EventData):
    """
    A Channel Update.
    You can listen to this event via the ``event_eventsub_channel_update`` event or via :ref:`subclassing the EventSub client <eventsub_subclass_ref>`.

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel being updated
    title: :class:`str`
        The updated title of the channel.
    language: :class:`str`
        The language the channel is broadcasting in.
    category_id: :class:`str`
        The ID of the category being streamed.
    category_name: :class:`str`
        The name of the category being streamed (usually a game name).
    """

    __slots__ = ("broadcaster", "title", "language", "category_id", "category_name", "is_mature")
    _dispatches_as = "channel_update"
    _required_scopes = None
    _version = 1
    _event = "channel.update"

    def __init__(self, transport: BaseTransport, payload: ChannelUpdatePayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_", payload)
        self.title: str = payload["title"]
        self.language: str = payload["language"]
        self.category_id: str = payload["category_id"]
        self.category_name: str = payload["category_name"]
        self.is_mature: bool = payload["is_mature"]


class ChannelFollow(EventData):
    """
    A channel follow. Indicates someone followed the broadcaster.

    Attributes
    -----------
    user: :class:`PartialUser`
        The user who followed.
    broadcaster: :class:`PartialUser`
        The user who received the follow.
    followed_at: :class:`datetime.datetime`
        The time the follow happened.
    """

    __slots__ = ("user", "broadcaster", "followed_at")
    _dispatches_as = "channel_follow"
    _required_scopes = ("moderator:read:followers",)
    _version = 2
    _event = "channel.follow"

    def __init__(self, transport: BaseTransport, payload: ChannelFollowPayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.followed_at: datetime.datetime = parse_timestamp(payload["followed_at"])


class ChannelSubscribe(EventData):
    """
    A channel subscription. Indicates someone subscribed to the channel. This does not include resubscriptions.

    Attributes
    -----------
    user: :class:`PartialUser`
        The user who subscribed.
    broadcaster: :class:`PartialUser`
        The channel that the user subscribed to.
    tier: Literal[1000, 2000, 3000]
        The tier of the subscription.
    is_gift: :class:`bool`
        Whether someone gifted the sub to the subscriber.
    """

    __slots__ = ("user", "broadcaster", "tier", "is_gift")
    _dispatches_as = "channel_subscribe"
    _required_scopes = ("channel:read:subscriptions",)
    _version = 1
    _event = "channel.subscribe"

    def __init__(self, transport: BaseTransport, payload: ChannelSubscribePayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.tier: Literal[1000, 2000, 3000] = int(payload["tier"])  # type: ignore
        self.is_gift: bool = payload["is_gift"]


class ChannelSubscribeEnd(EventData):
    """
    The end of a channel subscription. Indicates that someone has unsubscribed from the channel.

    Attributes
    -----------
    user: :class:`PartialUser`
        The user who subscribed.
    broadcaster: :class:`PartialUser`
        The channel that the user subscribed to.
    tier: Literal[1000, 2000, 3000]
        The tier of the subscription.
    is_gift: :class:`bool`
        Whether someone gifted the sub to the subscriber.
    """

    __slots__ = ("user", "broadcaster", "tier", "is_gift")
    _dispatches_as = "channel_subscribe_end"
    _required_scopes = ("channel:read:subscriptions",)
    _version = 1
    _event = "channel.subscription.end"

    def __init__(self, transport: BaseTransport, payload: ChannelSubscribeEndPayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.tier: Literal[1000, 2000, 3000] = int(payload["tier"])  # type: ignore
        self.is_gift: bool = payload["is_gift"]


class ChannelSubscribeGift(EventData):
    """
    A gifted subscription to a channel. This could be one or more gifts.

    Attributes
    -----------
    user: :class:`PartialUser` | ``None``
        The user who gave the gifts. Could be ``None`` if the gift is anonymous.
    broadcaster: :class:`PartialUser`
        The channel that the user subscribed to.
    total: :class:`int`
        How many gifts were given.
    cumulative_total: :class:`int` | ``None``
        How many gifts the user has given in total. This can be ``None`` if the gift is anonymous or the user doesn't share this.
    tier: Literal[1000, 2000, 3000]
        The tier of the subscription.
    is_anonymous: :class:`bool`
        Whether the gifter is anonymous or not.
    """

    __slots__ = ("user", "broadcaster", "total", "cumulative_total", "tier", "is_anonymous")
    _dispatches_as = "channel_subscribe_gift"
    _required_scopes = ("channel:read:subscriptions",)
    _version = 1
    _event = "channel.subscription.gift"

    def __init__(self, transport: BaseTransport, payload: ChannelSubscriptionGiftPayload) -> None:
        self.user: PartialUser | None = _transform_user(transport, "user_", payload) if payload["user_id"] else None
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.total: int = payload["total"]
        self.cumulative_total: int | None = int(payload["cumulative_total"])
        self.tier: Literal[1000, 2000, 3000] = int(payload["tier"])  # type: ignore
        self.is_anonymous: bool = payload["is_anonymous"]


class ChannelSubscribeMessage(EventData):
    """
    A resubscription message, as seen in chat.

    Attributes
    -----------
    user: :class:`PartialUser`
        The user who gave the gifts.
    broadcaster: :class:`PartialUser`
        The channel that the user subscribed to.
    message: :class:`str`
        The message sent to chat.
    emotes: list[dict[Literal["begin", "end", "id"], int | str]]
        Emotes in the message.
    cumulative_months: :class:`int`
        How many total months the user has subscribed to the channel.
    stream_moths: :class:`int` | ``None``
        How many months in a row the user has been subscribed to the channel. ``None`` if not shared by the user.
    tier: Literal[1000, 2000, 3000]
        The tier of the subscription.
    duration_months: :class:`bool`
        The month duration of the subscription.
    """

    __slots__ = (
        "user",
        "broadcaster",
        "message",
        "emotes",
        "cumulative_months",
        "streak_months",
        "tier",
        "duration_months",
    )
    _dispatches_as = "channel_subscribe_message"
    _required_scopes = ("channel:read:subscriptions",)
    _version = 1
    _event = "channel.subscription.message"

    def __init__(self, transport: BaseTransport, payload: ChannelSubscriptionMessagePayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.message: str = payload["message"]["text"]
        self.emotes: list[dict[Literal["begin", "end", "id"], str | int]] = payload["message"]["emotes"]  # type: ignore
        self.cumulative_months: int = payload["cumulative_months"]
        self.streak_months: int | None = payload["streak_months"]
        self.tier: Literal[1000, 2000, 3000] = int(payload["tier"])  # type: ignore
        self.duration_months: int = payload["duration_months"]


class ChannelCheer(EventData):
    """
    A cheer on a channel. Someone sent an amount of bits.

    Attributes
    -----------
    user: :class:`PartialUser` | ``None``
        The user who gave the gifts. Could be ``None`` if the gifter was anonymous.
    broadcaster: :class:`PartialUser`
        The channel that the user subscribed to.f
    message: :class:`str`
        The message sent to chat.
    bits: :class:`int`
        The amount of bits sent.
    is_anonymous: :class:`bool`
        Whether the bits were anonymous or not.
    """

    __slots__ = ("user", "broadcaster", "message", "bits", "is_anonymous")
    _dispatches_as = "channel_cheer"
    _required_scopes = ("bits:read",)
    _version = 1
    _event = "channel.cheer"

    def __init__(self, transport: BaseTransport, payload: ChannelCheerPayload) -> None:
        self.user: PartialUser | None = _transform_user(transport, "user_", payload) if payload["user_id"] else None
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.message: str = payload["message"]
        self.bits: int = payload["bits"]
        self.is_anonymous: bool = payload["is_anonymous"]


class ChannelBan(EventData):
    """
    A channel ban or timeout. Indicates someone was banned from the channel's chat.

    Attributes
    -----------
    user: :class:`PartialUser`
        The user who was banned.
    broadcaster: :class:`PartialUser`
        The channel from which the user was banned.
    moderator: :class:`PartialUser`
        The moderator who banned the user.
    reason: :class:`str`
        The reason the moderator banned the user.
    banned_at: :class:`datetime.datetime`
        When the ban occurred.
    ends_at: :class:`datetime.datetime` | ``None``
        When the timeout ends. ``None`` if it is a ban (permanent).
    is_permanent: :class:`bool`
        Whether the ban is permanent or a timeout.
    """

    __slots__ = ("user", "broadcaster", "moderator", "reason", "banned_at", "ends_at", "is_permanent")
    _dispatches_as = "channel_ban"
    _required_scopes = ("channel:moderate",)
    _version = 1
    _event = "channel.ban"

    def __init__(self, transport: BaseTransport, payload: ChannelBanPayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.moderator: PartialUser = _transform_user(transport, "moderator_user_", payload)
        self.reason: str = payload["reason"]
        self.banned_at: datetime.datetime = parse_timestamp(payload["banned_at"])
        self.ends_at: datetime.datetime | None = parse_timestamp(payload["ends_at"]) if payload["ends_at"] else None
        self.is_permanent: bool = payload["is_permanent"]


class ChannelGoalBegin(EventData):
    """
    A goal begin event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The broadcaster that started the goal
    id: :class:`str`
        The ID of the goal event.
    type: :class:`str`
        The goal type.
    description: :class:`str`
        The goal description.
    current_amount: :class:`int`
        The goal current amount.
    target_amount: :class:`int`
        The goal target amount.
    started_at: :class:`datetime.datetime`
        The datetime the goal was started.
    """

    __slots__ = ("user", "id", "type", "description", "current_amount", "target_amount", "started_at")
    _dispatches_as = "channel_goal_begin"
    _required_scopes = ("channel:read:goals",)
    _version = 1
    _event = "channel.goal.begin"

    def __init__(self, transport: BaseTransport, payload: ChannelGoalBeginProgressPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.id: str = payload["id"]
        self.type: str = payload["type"]
        self.description: str = payload["description"]
        self.current_amount: int = payload["current_amount"]
        self.target_amount: int = payload["target_amount"]
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])


class ChannelGoalProgress(EventData):
    """
    A goal begin event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The broadcaster that started the goal
    id: :class:`str`
        The ID of the goal event.
    type: :class:`str`
        The goal type.
    description: :class:`str`
        The goal description.
    current_amount: :class:`int`
        The goal current amount.
    target_amount: :class:`int`
        The goal target amount.
    started_at: :class:`datetime.datetime`
        The datetime the goal was started.
    """

    __slots__ = ("user", "id", "type", "description", "current_amount", "target_amount", "started_at")
    _dispatches_as = "channel_goal_progress"
    _required_scopes = ("channel:read:goals",)
    _version = 1
    _event = "channel.goal.progress"

    def __init__(self, transport: BaseTransport, payload: ChannelGoalBeginProgressPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.id: str = payload["id"]
        self.type: str = payload["type"]
        self.description: str = payload["description"]
        self.current_amount: int = payload["current_amount"]
        self.target_amount: int = payload["target_amount"]
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])


class ChannelGoalEnd(EventData):
    """
    A goal begin event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The broadcaster that started the goal
    id: :class:`str`
        The ID of the goal event.
    type: :class:`str`
        The goal type.
    description: :class:`str`
        The goal description.
    current_amount: :class:`int`
        The goal current amount.
    target_amount: :class:`int`
        The goal target amount.
    started_at: :class:`datetime.datetime`
        The datetime the goal was started.
    """

    __slots__ = (
        "user",
        "id",
        "type",
        "description",
        "current_amount",
        "target_amount",
        "started_at",
        "ended_at",
        "is_achieved",
    )
    _dispatches_as = "channel_goal_end"
    _required_scopes = ("channel:read:goals",)
    _version = 1
    _event = "channel.goal.end"

    def __init__(self, transport: BaseTransport, payload: ChannelGoalEndPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.id: str = payload["id"]
        self.type: str = payload["type"]
        self.description: str = payload["description"]
        self.current_amount: int = payload["current_amount"]
        self.target_amount: int = payload["target_amount"]
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])
        self.ended_at: datetime.date = parse_timestamp(payload["ended_at"])
        self.is_achieved: bool = payload["is_achieved"]


class ChannelUnban(EventData):
    """
    A Channel Unban event

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user that was unbanned.
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the unban occurred in.
    moderator: :class`twitchio.PartialUser`
        The moderator that performed the unban.
    """

    __slots__ = ("user", "broadcaster", "moderator")
    _dispatches_as = "channel_unban"
    _required_scopes = ("channel:moderate",)
    _version = 1
    _event = "channel.unban"

    def __init__(self, transport: BaseTransport, payload: ChannelUnbanPayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.moderator: PartialUser = _transform_user(transport, "moderator_user_", payload)


class ChannelRaid(EventData):
    """
    A Raid event

    Attributes
    -----------
    raider: :class:`~twitchio.PartialUser`
        The person initiating the raid.
    reciever: :class:`~twitchio.PartialUser`
        The person recieving the raid.
    viewer_count: :class:`int`
        The amount of people raiding.
    """

    __slots__ = ("raider", "reciever", "viewer_count")
    _dispatches_as = "channel_raid"
    _required_scopes = None
    _version = 1
    _event = "channel.raid"

    def __init__(self, transport: BaseTransport, payload: ChannelRaidPayload) -> None:
        self.raider: PartialUser = _transform_user(transport, "from_broadcaster_user_", payload)
        self.reciever: PartialUser = _transform_user(transport, "to_broadcaster_user_", payload)
        self.viewer_count: int = payload["viewers"]


class ChannelModeratorAdd(EventData):
    """
    Moderator added to channel

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user being added as a moderator.
    broadcaster: :class:`~twitchio.PartialUser`
        The channel that is having a moderator added.
    """

    __slots__ = ("broadcaster", "user")
    _dispatches_as = "channel_moderator_add"
    _required_scopes = ("moderation:read",)
    _version = 1
    _event = "channel.moderator.add"

    def __init__(self, transport: BaseTransport, payload: ChannelModeratorAddPayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)


class ChannelModeratorRemove(EventData):
    """
    Moderator removed from channel

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user being removed from moderator status.
    broadcaster: :class:`~twitchio.PartialUser`
        The channel that is having a moderator removed.
    """

    __slots__ = ("broadcaster", "user")
    _dispatches_as = "channel_moderator_remove"
    _required_scopes = ("moderation:read",)
    _version = 1
    _event = "channel.moderator.remove"

    def __init__(self, transport: BaseTransport, payload: ChannelModeratorRemovePayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)


class StreamOnline(EventData):
    """
    A Stream Start event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel that went live.
    id: :class:`str`
        Some sort of ID for the stream.
    type: :class:`str`
        One of "live", "playlist", "watch_party", "premier", or "rerun". The type of live event.
    started_at: :class:`datetime.datetime`
        The time when the stream started.
    """

    __slots__ = ("broadcaster", "id", "type", "started_at")
    _dispatches_as = "stream_online"
    _required_scopes = None
    _version = 1
    _event = "stream.online"

    def __init__(self, transport: BaseTransport, payload: StreamOnlinePayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.id: str = payload["id"]
        self.type: Literal["live", "playlist", "watch_party", "premier", "rerun"] = payload["type"]
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])


class StreamOffline(EventData):
    """
    A Stream Offline event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel that went live.
    """

    __slots__ = ("broadcaster",)
    _dispatches_as = "stream_offline"
    _required_scopes = None
    _version = 1
    _event = "stream.offline"

    def __init__(self, transport: BaseTransport, payload: StreamOfflinePayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)


class UserAuthorizationGrant(EventData):
    """
    An Authorization Granted event

    This subscription type is only supported by webhooks.
    Provided client_id must match the client id in the application access token.

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user that has granted authorization for your app.
    client_id: :class:`str`
        The client id of the app that had its authorization granted.
    """

    __slots__ = ("client_id", "user")
    _dispatches_as = "user_authorization_grant"
    _required_scopes = None
    _version = 1
    _event = "user.authorization.grant"

    def __init__(self, transport: BaseTransport, payload: UserAuthorizationGrantPayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.client_id: str = payload["client_id"]


class UserAuthorizationRevoke(EventData):
    """
    An Authorization Revoke event

    This subscription type is only supported by webhooks.
    Provided client_id must match the client id in the application access token.

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user that has revoked authorization for your app.
    client_id: :class:`str`
        The client id of the app that had its authorization revoked.
    """

    __slots__ = ("client_id", "user")
    _dispatches_as = "user_authorization_revoke"
    _required_scopes = None
    _version = 1
    _event = "user.authorization.revoke"

    def __init__(self, transport: BaseTransport, payload: UserAuthorizationRevokePayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.client_id: str = payload["client_id"]


class UserUpdate(EventData):
    """
    A User Update event

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user that was updated
    email: Optional[:class:`str`]
        The users email, if you have permission to read this information
    description: :class:`str`
        The channels description (displayed as ``bio``)
    """

    __slots__ = ("user", "email", "description", "email_verified")
    _dispatches_as = "user_authorization_revoke"
    _required_scopes = ("user:read:email",)
    _version = 1
    _event = "user.update"

    def __init__(self, transport: BaseTransport, payload: UserUpdatePayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.email: str | None = payload.get("email")
        self.description: str = payload["description"]
        self.email_verified: bool = payload["email_verified"]


class HypeTrainContributor:
    """
    A Contributor to a Hype Train

    Attributes
    -----------
    user: :class:`~twitchio.PartialUser`
        The user.
    type: :class:`str`
        One of "bits, "subscription" or "other". The way they contributed to the hype train.
    total: :class:`int`
        How many points they've contributed to the Hype Train.
    """

    __slots__ = ("user", "type", "total")

    def __init__(self, transport: BaseTransport, payload: ChannelHypeTrain_ContributorPayload) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.type: Literal["bits", "subscription", "other"] = payload["type"]  # one of bits, subscription
        self.total: int = payload["total"]


class ChannelHypeTrainBegin(EventData):
    """
    A Hype Train Begin event

    Attributes
    -----------

    broadcaster: :class:`~twitchio.PartialUser`
        The channel the Hype Train occurred in.
    total_points: :class:`int`
        The total amounts of points in the Hype Train.
    progress: :class:`int`
        The progress of the Hype Train towards the next level.
    goal: :class:`int`
        The goal to reach the next level.
    started: :class:`datetime.datetime`
        When the Hype Train started.
    expires: :class:`datetime.datetime`
        When the Hype Train ends.
    top_contributions: List[:class:`HypeTrainContributor`]
        The top contributions of the Hype Train.
    last_contribution: :class:`HypeTrainContributor`
        The last contributor to the Hype Train.
    level: :class:`int`
        The current level of the Hype Train.
    """

    __slots__ = (
        "broadcaster",
        "total_points",
        "progress",
        "goal",
        "top_contributions",
        "last_contribution",
        "started",
        "expires",
        "level",
    )
    _dispatches_as = "channel_hypetrain_begin"
    _required_scopes = ("channel:read:hype_train",)
    _version = 1
    _event = "channel.hype_train.begin"

    def __init__(self, transport: BaseTransport, payload: ChannelHypeTrainBeginProgressPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.total_points: int = payload["total"]
        self.progress: int = payload["progress"]
        self.goal: int = payload["goal"]
        self.started: datetime.datetime = parse_timestamp(payload["started_at"])
        self.expires: datetime.datetime = parse_timestamp(payload["expires_at"])
        self.top_contributions: list[HypeTrainContributor] = [
            HypeTrainContributor(transport, d) for d in payload["top_contributions"]
        ]
        self.last_contribution: HypeTrainContributor = HypeTrainContributor(transport, payload["last_contribution"])
        self.level: int = payload["level"]


class ChannelHypeTrainProgress(EventData):
    """
    A Hype Train Progress event

    Attributes
    -----------

    broadcaster: :class:`~twitchio.PartialUser`
        The channel the Hype Train occurred in.
    total_points: :class:`int`
        The total amounts of points in the Hype Train.
    progress: :class:`int`
        The progress of the Hype Train towards the next level.
    goal: :class:`int`
        The goal to reach the next level.
    started: :class:`datetime.datetime`
        When the Hype Train started.
    expires: :class:`datetime.datetime`
        When the Hype Train ends.
    top_contributions: List[:class:`HypeTrainContributor`]
        The top contributions of the Hype Train.
    last_contribution: :class:`HypeTrainContributor`
        The last contributor to the Hype Train.
    level: :class:`int`
        The current level of the Hype Train.
    """

    __slots__ = (
        "broadcaster",
        "total_points",
        "progress",
        "goal",
        "top_contributions",
        "last_contribution",
        "started",
        "expires",
        "level",
    )
    _dispatches_as = "channel_hypetrain_progress"
    _required_scopes = ("channel:read:hype_train",)
    _version = 1
    _event = "channel.hype_train.progress"

    __init__ = ChannelHypeTrainBegin.__init__


class ChannelHypeTrainEnd(EventData):
    """
    A Hype Train End event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the Hype Train occurred in.
    total_points: :class:`int`
        The total amounts of points in the Hype Train.
    level: :class:`int`
        The level the hype train reached.
    started: :class:`datetime.datetime`
        When the Hype Train started.
    top_contributions: List[:class:`HypeTrainContributor`]
        The top contributions of the Hype Train.
    cooldown_ends_at: :class:`datetime.datetime`
        When another Hype Train can begin.
    """

    __slots__ = ("broadcaster", "level", "total_points", "top_contributions", "started", "ended", "cooldown_ends_at")
    _dispatches_as = "channel_hypetrain_end"
    _required_scopes = ("channel:read:hype_train",)
    _version = 1
    _event = "channel.hype_train.end"

    def __init__(self, transport: BaseTransport, payload: ChannelHypeTrainEndPayload) -> None:
        self.broadcaster = _transform_user(transport, "broadcaster_user_", payload)
        self.total_points: int = payload["total"]
        self.level: int = payload["level"]
        self.started: datetime.datetime = parse_timestamp(payload["started_at"])
        self.ended: datetime.datetime = parse_timestamp(payload["ended_at"])
        self.cooldown_ends_at: datetime.datetime = parse_timestamp(payload["cooldown_ends_at"])
        self.top_contributions: list[HypeTrainContributor] = [
            HypeTrainContributor(transport, d) for d in payload["top_contributions"]
        ]


_event_map: dict[str, Type[EventData]] = {t._event: t for t in EventData.__subclasses__()}  # type: ignore
AllModels = Union[
    ChannelBan,
    ChannelCheer,
    ChannelFollow,
    ChannelGoalBegin,
    ChannelGoalEnd,
    ChannelGoalProgress,
    ChannelModeratorAdd,
    ChannelModeratorRemove,
    ChannelUnban,
    ChannelUpdate,
    ChannelSubscribe,
    ChannelSubscribeEnd,
    ChannelSubscribeGift,
    ChannelSubscribeMessage,
    ChannelRaid,
    StreamOnline,
    StreamOffline,
    UserAuthorizationGrant,
    UserAuthorizationRevoke,
    UserUpdate,
    ChannelHypeTrainBegin,
    ChannelHypeTrainProgress,
    ChannelHypeTrainEnd,
]
