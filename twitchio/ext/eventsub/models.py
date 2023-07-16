from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Mapping, Protocol, Type, Union

from twitchio import PartialUser
from twitchio.utils import copy_doc, parse_timestamp

if TYPE_CHECKING:
    import datetime

    from .transport import BaseTransport
    from .types.payloads import (
        ChannelBan as ChannelBanPayload,
        ChannelCheer as ChannelCheerPayload,
        ChannelCustomReward_global_cooldown as ChannelCustomReward_global_cooldownPayload,
        ChannelCustomReward_streamlimits as ChannelCustomReward_streamlimitsPayload,
        ChannelCustomRewardModify as ChannelCustomRewardModifyPayload,
        ChannelCustomRewardRedemptionModify as ChannelCustomRewardRedemptionModifyPayload,
        ChannelCustomRewardRedemptionModify_Reward as ChannelCustomRewardRedemptionModify_RewardPayload,
        ChannelFollow as ChannelFollowPayload,
        ChannelGoalBeginProgress as ChannelGoalBeginProgressPayload,
        ChannelGoalEnd as ChannelGoalEndPayload,
        ChannelHypeTrain_Contributor as ChannelHypeTrain_ContributorPayload,
        ChannelHypeTrainBeginProgress as ChannelHypeTrainBeginProgressPayload,
        ChannelHypeTrainEnd as ChannelHypeTrainEndPayload,
        ChannelModeratorAdd as ChannelModeratorAddPayload,
        ChannelModeratorRemove as ChannelModeratorRemovePayload,
        ChannelPollBegin as ChannelPollBeginPayload,
        ChannelPollBegin_Choice as ChannelPollBegin_ChoicePayload,
        ChannelPollEnd as ChannelPollEndPayload,
        ChannelPredictionBegin as ChannelPredictionBeginPayload,
        ChannelPredictionBegin_outcomes as ChannelPredictionBegin_outcomesPayload,
        ChannelPredictionEnd as ChannelPredictionEndPayload,
        ChannelPredictionProgressLock as ChannelPredictionProgressLockPayload,
        ChannelRaid as ChannelRaidPayload,
        ChannelShoutoutCreate as ChannelShoutoutCreatePayload,
        ChannelShoutoutReceive as ChannelShoutoutReceivePayload,
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
    "HypeTrainContributor",
    "ChannelHypeTrainBegin",
    "ChannelHypeTrainProgress",
    "ChannelHypeTrainEnd",
    "PollStatus",
    "PollChoice",
    "ChannelPollBegin",
    "ChannelPollProgress",
    "ChannelPollEnd",
    "Predictor",
    "PredictionOutcome",
    "PredictionStatus",
    "ChannelPredictionBegin",
    "ChannelPredictionProgress",
    "ChannelPredictionLock",
    "ChannelPredictionEnd",
    "ChannelCustomReward",
    "ChannelCustomRewardAdd",
    "ChannelCustomRewardUpdate",
    "ChannelCustomRewardRemove",
    "PartialReward",
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
    _required_scopes: tuple[str, ...] | None  # any of the scopes can be used, they're not all required
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
        Requires the ``user:read:email`` scope
    description: :class:`str`
        The channels description (displayed as ``bio``)
    """

    __slots__ = ("user", "email", "description", "email_verified")
    _dispatches_as = "user_authorization_revoke"
    _required_scopes = None
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


class PollStatus(Enum):
    """
    The status of a poll.

    ACTIVE: Poll is currently in progress.
    COMPLETED: Poll has reached its `ended_at` time.
    TERMINATED: Poll has been manually terminated before its `ended_at` time.
    ARCHIVED: Poll is no longer visible on the channel.
    MODERATED: Poll is no longer visible to any user on Twitch.
    INVALID: Something went wrong determining the state.
    """

    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    ARCHIVED = "archived"
    MODERATED = "moderated"
    INVALID = "invalid"


class PollChoice:
    """
    A Poll Choice

    Attributes
    -----------
    choice_id: :class:`str`
        The ID of the choice
    title: :class:`str`
        The title of the choice
    channel_points_votes: :class:`int`
        How many votes were cast using Channel Points
    votes: :class:`int`
        The total number of votes
    """

    __slots__ = "choice_id", "title", "channel_points_votes", "votes"

    def __init__(self, data: ChannelPollBegin_ChoicePayload):
        self.choice_id: str = data["id"]
        self.title: str = data["title"]
        self.channel_points_votes: int = data.get("channel_points_votes", 0)
        self.votes: int = data.get("votes", 0)


class ChannelPollBegin(EventData):
    """
    A Poll Begin event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the poll occured in.
    poll_id: :class:`str`
        The ID of the poll.
    title: :class:`str`
        The title of the poll.
    choices: List[:class:`PollChoice`]
        The choices in the poll.
    cost_per_vote: :class:`int`
        How many channel points it takes to cast a vote.
    started_at: :class:`datetime.datetime`
        When the poll started.
    ends_at: :class:`datetime.datetime`
        When the poll is set to end.
    """

    __slots__ = (
        "broadcaster",
        "poll_id",
        "title",
        "choices",
        "bits_voting",
        "cost_per_vote",
        "started_at",
        "ends_at",
    )
    _dispatches_as = "channel_poll_begin"
    _required_scopes = ("channel:read:polls", "channel:manage:polls")
    _version = 1
    _event = "channel.poll.begin"

    def __init__(self, transport: BaseTransport, payload: ChannelPollBeginPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.poll_id: str = payload["id"]
        self.title: str = payload["title"]
        self.choices = [PollChoice(c) for c in payload["choices"]]
        self.cost_per_vote: int = payload["channel_points_voting"][
            "amount_per_vote"
        ]  # bits voting is not a thing anymore, so this is the forced default
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])
        self.ends_at: datetime.datetime = parse_timestamp(payload["ends_at"])


class ChannelPollProgress(EventData):
    """
    A Poll Progress event. dispatched when a poll received an update to votes

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the poll occured in.
    poll_id: :class:`str`
        The ID of the poll.
    title: :class:`str`
        The title of the poll.
    choices: List[:class:`PollChoice`]
        The choices in the poll.
    cost_per_vote: :class:`int`
        How many channel points it takes to cast a vote.
    started_at: :class:`datetime.datetime`
        When the poll started.
    ends_at: :class:`datetime.datetime`
        When the poll is set to end.
    """

    __slots__ = (
        "broadcaster",
        "poll_id",
        "title",
        "choices",
        "bits_voting",
        "cost_per_vote",
        "started_at",
        "ends_at",
    )
    _dispatches_as = "channel_poll_progress"
    _required_scopes = ("channel:read:polls", "channel:manage:polls")
    _version = 1
    _event = "channel.poll.progress"

    __init__ = ChannelPollBegin.__init__


class ChannelPollEnd(EventData):
    """
    A Poll End event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the poll occured in.
    poll_id: :class:`str`
        The ID of the poll.
    title: :class:`str`
        The title of the poll.
    choices: List[:class:`PollChoice`]
        The choices in the poll.
    cost_per_vote: :class:`int`
        How many channel points it takes to cast a vote.
    status: :class:`PollStatus`
        How the poll ended.
    started_at: :class:`datetime.datetime`
        When the poll started.
    ended_at: :class:`datetime.datetime`
        When the poll is set to end.
    """

    __slots__ = (
        "broadcaster",
        "poll_id",
        "title",
        "choices",
        "bits_voting",
        "cost_per_vote",
        "status",
        "started_at",
        "ended_at",
    )
    _dispatches_as = "channel_poll_end"
    _required_scopes = ("channel:read:polls", "channel:manage:polls")
    _version = 1
    _event = "channel.poll.end"

    def __init__(self, transport: BaseTransport, payload: ChannelPollEndPayload) -> None:
        self.broadcaster = _transform_user(transport, "broadcaster_user_", payload)
        self.poll_id: str = payload["id"]
        self.title: str = payload["title"]
        self.choices: list[PollChoice] = [PollChoice(c) for c in payload["choices"]]
        self.cost_per_vote: int = payload["channel_points_voting"]["amount_per_vote"]
        self.status = PollStatus(payload["status"].lower())
        self.started_at = parse_timestamp(payload["started_at"])
        self.ended_at = parse_timestamp(payload["ended_at"])


class Predictor:
    """
    A Predictor

    Attributes
    -----------
    user: :class:`twitchio.PartialUser`
        The user who predicted an outcome
    channel_points_used: :class:`int`
        How many Channel Points the user used to predict this outcome
    channel_points_won: :class:`int`
        How many Channel Points was distributed to the user.
        Will be ``None`` if the Prediction is unresolved, cancelled (refunded), or the user predicted the losing outcome.
    """

    __slots__ = "user", "channel_points_used", "channel_points_won"

    def __init__(self, transport: BaseTransport, data: dict):
        self.user: PartialUser = _transform_user(transport, "user_", data)
        self.channel_points_used: int = data["channel_points_used"]
        self.channel_points_won: int | None = data["channel_points_won"]


class PredictionOutcome:
    """
    A Prediction Outcome

    Attributes
    -----------
    outcome_id: :class:`str`
        The ID of the outcome
    title: :class:`str`
        The title of the outcome
    channel_points: :class:`int`
        The amount of Channel Points that have been bet for this outcome
    color: :class:`str`
        The color of the outcome. Can be `blue` or `pink`
    users: :class:`int`
        The number of users who predicted the outcome
    top_predictors: List[:class:`Predictor`]
        The top predictors of the outcome
    """

    __slots__ = "outcome_id", "title", "channel_points", "color", "users", "top_predictors"

    def __init__(self, transport: BaseTransport, data: ChannelPredictionBegin_outcomesPayload):
        self.outcome_id: str = data["id"]
        self.title: str = data["title"]
        self.channel_points: int = data.get("channel_points", 0)
        self.color: str = data["color"]
        self.users: int = data.get("users", 0)
        self.top_predictors: list[Predictor] = [Predictor(transport, x) for x in data.get("top_predictors", [])]

    @property
    def colour(self) -> str:
        """The colour of the prediction. Alias to color."""
        return self.color


class PredictionStatus(Enum):
    """
    The status of a Prediction.

    ACTIVE: Prediction is active and viewers can make predictions.
    LOCKED: Prediction has been locked and viewers can no longer make predictions.
    RESOLVED: A winning outcome has been chosen and the Channel Points have been distributed to the users who guessed the correct outcome.
    CANCELED: Prediction has been canceled and the Channel Points have been refunded to participants.
    """

    ACTIVE = "active"
    LOCKED = "locked"
    RESOLVED = "resolved"
    CANCELED = "canceled"


class ChannelPredictionBegin(EventData):
    """
    A Prediction Begin event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the prediction occured in.
    prediction_id: :class:`str`
        The ID of the prediction,
    title: :class:`str`
        The title of the prediction.
    outcomes: List[:class:`PredictionOutcome`]
        The outcomes for the prediction.
    started_at: :class:`datetime.datetime`
        When the prediction started.
    locks_at: :class:`datetime.datetime`
        When the prediction is set to be locked.
    """

    _dispatches_as = "channel_prediction_begin"
    _required_scopes = ("channel:read:predictions", "channel:manage:predictions")
    _version = 1
    _event = "channel.prediction.begin"

    __slots__ = ("broadcaster", "prediction_id", "title", "outcomes", "started_at", "locks_at")

    def __init__(self, transport: BaseTransport, payload: ChannelPredictionBeginPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.prediction_id: str = payload["id"]
        self.title: str = payload["title"]
        self.outcomes: list[PredictionOutcome] = [PredictionOutcome(transport, x) for x in payload["outcomes"]]
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])
        self.locks_at: datetime.datetime = parse_timestamp(payload["locks_at"])


class ChannelPredictionProgress(EventData):
    """
    A Prediction Progress event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the prediction occured in.
    prediction_id: :class:`str`
        The ID of the prediction,
    title: :class:`str`
        The title of the prediction.
    outcomes: List[:class:`PredictionOutcome`]
        The outcomes for the prediction.
    started_at: :class:`datetime.datetime`
        When the prediction started.
    locks_at: :class:`datetime.datetime`
        When the prediction is set to be locked.
    """

    __slots__ = ("broadcaster", "prediction_id", "title", "outcomes", "started_at", "locks_at")
    _dispatches_as = "channel_prediction_progress"
    _required_scopes = ("channel:read:predictions", "channel:manage:predictions")
    _version = 1
    _event = "channel.prediction.progress"

    __init__ = ChannelPredictionBegin.__init__


class ChannelPredictionLock(EventData):
    """
    A Prediction Lock event

    Attributes
    -----------
    broadcaster: :class:`twitchio.PartialUser`
        The channel the prediction occured in.
    prediction_id: :class:`str`
        The ID of the prediction.
    title: :class:`str`
        The title of the prediction.
    outcomes: List[:class:`PredictionOutcome`]
        The outcomes for the prediction.
    started_at: :class:`datetime.datetime`
        When the prediction started.
    locked_at: :class:`datetime.datetime`
        When the prediction was locked.
    """

    __slots__ = ("broadcaster", "prediction_id", "title", "outcomes", "started_at", "locked_at")
    _dispatches_as = "channel_prediction_lock"
    _required_scopes = ("channel:read:predictions", "channel:manage:predictions")
    _version = 1
    _event = "channel.prediction.lock"

    def __init__(self, transport: BaseTransport, payload: ChannelPredictionProgressLockPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.prediction_id: str = payload["id"]
        self.title: str = payload["title"]
        self.outcomes: list[PredictionOutcome] = [PredictionOutcome(transport, x) for x in payload["outcomes"]]
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])
        self.locked_at: datetime.datetime = parse_timestamp(payload["locked_at"])


class ChannelPredictionEnd(EventData):
    """
    A Prediction Begin/Progress event

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The channel the prediction occured in
    prediction_id: :class:`str`
        The ID of the prediction
    title: :class:`str`
        The title of the prediction
    winning_outcome_id: :class:`str`
        The ID of the outcome that won
    outcomes: List[:class:`PredictionOutcome`]
        The outcomes for the prediction
    status: :class:`PredictionStatus`
        How the prediction ended
    started_at: :class:`datetime.datetime`
        When the prediction started
    ended_at: :class:`datetime.datetime`
        When the prediction ended
    """

    __slots__ = (
        "broadcaster",
        "prediction_id",
        "title",
        "winning_outcome_id",
        "outcomes",
        "status",
        "started_at",
        "ended_at",
    )
    _dispatches_as = "channel_prediction_end"
    _required_scopes = ("channel:read:predictions", "channel:manage:predictions")
    _version = 1
    _event = "channel.prediction.end"

    def __init__(self, transport: BaseTransport, payload: ChannelPredictionEndPayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_user_", payload)
        self.prediction_id: str = payload["id"]
        self.title: str = payload["title"]
        self.winning_outcome_id: str = payload["winning_outcome_id"]
        self.outcomes: list[PredictionOutcome] = [PredictionOutcome(transport, x) for x in payload["outcomes"]]
        self.status: PredictionStatus = PredictionStatus(payload["status"].lower())
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])
        self.ended_at: datetime.datetime = parse_timestamp(payload["ended_at"])


class ChannelCustomReward_streamlimits:
    """
    Indicates what redemption limits are applied to this reward per stream.

    Attributes
    -----------
    enabled: :class:`bool`
        Are the limits enabled.
    value: :class:`int`
        The maximum amount of times this reward can be redeemed per stream.
    """

    __slots__ = ("enabled", "value")

    def __init__(self, payload: ChannelCustomReward_streamlimitsPayload) -> None:
        self.enabled: bool = payload["is_enabled"]
        self.value: int = payload["value"]


class ChannelCustomReward_global_cooldown:
    """
    Indicates what cooldowns are applied globally when a reward is redeemed.

    Attributes
    -----------
    enabled: :class:`bool`
        Are the limits enabled.
    seconds: :class:`int`
        The cooldown after this reward is redeemed.
    """

    __slots__ = ("enabled", "seconds")

    def __init__(self, payload: ChannelCustomReward_global_cooldownPayload) -> None:
        self.enabled: bool = payload["is_enabled"]
        self.seconds: int = payload["seconds"]


class ChannelCustomReward:
    """
    A Custom Reward event

    Attributes
    -----------
    id: :class:`str`
        The ID of the reward.
    broadcaster: :class:`~twitchio.PartialUser`
        The channel on which the reward was modified.
    enabled: :class:`bool`
        Whether the reward is enabled.
    paused: :class:`bool`
        Whether the reward redemptions are paused.
    in_stock: :class:`bool`
        Whether the reward is in stock.
    title: :class:`str`
        The title of the reward
    cost: :class:`int`
        How many channel points are required to redeem this custom reward.
    prompt: :class:`str`
        The prompt given to users when redeeming this reward.
    user_input_required: :class:`bool`
        Whether the user will input a message when redeeming this reward.
    redemptions_skip_request_queue: :class:`bool`
        Whether redemptions will bypass the redemption request queue.
    cooldown_expires_at: :class:`datetime.datetime` | ``None``
        When the cooldown will expire, if on cooldown.
    amount_redeemed_current_stream: :class:`int` | ``None``
        How many of this reward have been redeemed during the current stream. ``None`` when not live.
    background_color: :class:`str`
        The background colour of the reward to viewers.
    max_per_stream: :class:`ChannelCustomReward_streamlimits`
        The max amount of this reward that can be redeemed in a stream.
    global_cooldown: :class:`ChannelCustomReward_global_cooldown`
        The global cooldown configuration for this reward.
    image: :class:`ImageLinks`
        The image for this reward.
    default_image: :class:`ImageLinks`
        The default image for this reward.
    """

    __slots__ = (
        "id",
        "broadcaster",
        "enabled",
        "paused",
        "in_stock",
        "title",
        "cost",
        "prompt",
        "user_input_required",
        "redemptions_skip_request_queue",
        "cooldown_expires_at",
        "amount_redeemed_current_stream",
        "background_color",
        "max_per_stream",
        "max_per_user_per_stream",
        "global_cooldown",
        "image",
        "default_image",
    )

    def __init__(self, transport: BaseTransport, payload: ChannelCustomRewardModifyPayload) -> None:
        self.id: str = payload["id"]
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_", payload)
        self.enabled: bool = payload["is_enabled"]
        self.paused: bool = payload["is_paused"]
        self.in_stock: bool = payload["is_in_stock"]
        self.title: str = payload["title"]
        self.cost: int = payload["cost"]
        self.prompt: str = payload["prompt"]
        self.user_input_required: bool = payload["is_user_input_required"]
        self.redemptions_skip_request_queue: bool = payload["should_redemptions_skip_request_queue"]
        self.cooldown_expires_at: datetime.datetime | None = (
            parse_timestamp(payload["cooldown_expires_at"]) if payload["cooldown_expires_at"] else None
        )
        self.amount_redeemed_current_stream: int | None = payload["redemptions_redeemed_current_stream"]
        self.background_color: str = payload["background_color"]
        self.max_per_stream: ChannelCustomReward_streamlimits = ChannelCustomReward_streamlimits(
            payload["max_per_stream"]
        )
        self.global_cooldown: ChannelCustomReward_global_cooldown = ChannelCustomReward_global_cooldown(
            payload["global_cooldown"]
        )
        self.image: ImageLinks = ImageLinks(payload["image"])
        self.default_image: ImageLinks = ImageLinks(payload["default_image"])


@copy_doc(ChannelCustomReward)
class ChannelCustomRewardAdd(ChannelCustomReward, EventData):
    _dispatches_as = "channel_reward_add"
    _required_scopes = ("channel:read:redemptions", "channel:manage:redemptions")
    _version = 1
    _event = "channel.channel_points_custom_reward.add"


@copy_doc(ChannelCustomReward)
class ChannelCustomRewardUpdate(ChannelCustomReward, EventData):
    _dispatches_as = "channel_reward_update"
    _required_scopes = ("channel:read:redemptions", "channel:manage:redemptions")
    _version = 1
    _event = "channel.channel_points_custom_reward.update"


@copy_doc(ChannelCustomReward)
class ChannelCustomRewardRemove(ChannelCustomReward, EventData):
    _dispatches_as = "channel_custom_reward_remove"
    _required_scopes = ("channel:read:redemptions", "channel:manage:redemptions")
    _version = 1
    _event = "channel.channel_points_custom_reward.remove"


class PartialReward:
    """
    A partial reward object, which provides limited information about the reward that was redeemed.

    Attributes
    -----------
    id: :class:`str`
        The ID of the reward.
    title: :class:`str
        The title of the reward.
    cost: :class:`int`
        The cost in channel points of the reward.
    prompt: :class:`str`
        The prompt the user received when redeeming the reward.
    """

    __slots__ = ("id", "title", "cost", "prompt")

    def __init__(self, payload: ChannelCustomRewardRedemptionModify_RewardPayload) -> None:
        self.id: str = payload["id"]
        self.title: str = payload["title"]
        self.cost: int = payload["cost"]
        self.prompt: str = payload["prompt"]


class ChannelCustomRewardRedemptionAdd(EventData):
    """
    A custom reward redemption creation/update event.

    Attributes
    -----------
    id: :class:`str`
        The ID of the redemption. Note that this is **not** the ID of the reward itself.
    broadcaster: :class:`~twitchio.PartialUser`
        The channel on which this reward was redeemed.
    user: :class:`~twitchio.PartialUser`
        The user that redeemed the reward.
    user_input: :class:`str` | ``None``
        The message the user wrote, if the reward requested one.
    status: literal["unfilfilled", "fulfilled", "cancelled"]
        The status of the redemption.
    reward: :class:`ChannelCustomReward`
        The reward that was redeemed.
    redeemed_at: :class:`datetime.datetime`
        When the reward was redeemed.
    """

    __slots__ = ("id", "broadcaster", "user", "user_input", "status", "reward", "redeemed_at")

    _dispatches_as = "channel_points_reward_redemption"
    _required_scopes = ("channel:read:redemptions", "channel:manage:redemptions")
    _version = 1
    _event = "channel.channel_points_custom_reward_redemption.add"

    def __init__(self, transport: BaseTransport, payload: ChannelCustomRewardRedemptionModifyPayload) -> None:
        self.id: str = payload["id"]
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_", payload)
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.user_input: str = payload["user_input"]
        self.status: Literal["unfulfilled", "fulfilled", "cancelled"] = payload["status"]
        self.reward: PartialReward = PartialReward(payload["reward"])
        self.redeemed_at = parse_timestamp(payload["redeemed_at"])


@copy_doc(ChannelCustomRewardRedemptionAdd)
class ChannelCustomRewardRedemptionUpdate(EventData):
    __slots__ = ("id", "broadcaster", "user", "user_input", "status", "reward", "redeemed_at")

    _dispatches_as = "channel_points_reward_redemption_update"
    _required_scopes = ("channel:read:redemptions", "channel:manage:redemptions")
    _version = 1
    _event = "channel.channel_points_custom_reward_redemption.update"

    def __init__(self, transport: BaseTransport, payload: ChannelCustomRewardRedemptionModifyPayload) -> None:
        self.id: str = payload["id"]
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_", payload)
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.user_input: str = payload["user_input"]
        self.status: Literal["unfulfilled", "fulfilled", "cancelled"] = payload["status"]
        self.reward: PartialReward = PartialReward(payload["reward"])
        self.redeemed_at = parse_timestamp(payload["redeemed_at"])


class ChannelShoutoutCreate(EventData):
    """
    A shoutout create event. This is created when a shoutout is created, not received.

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The broadcaster from which the shoutout is coming.
    moderator: :class:`~twitchio.PartialUser`
        The moderator that created the shoutout.
    target: :class:`~twitchio.PartialUser`
        The person receiving the shoutout.
    started_at: :class:`datetime.datetime`
        When the shoutout started.
    viewer_count: :class:`int`
        How many viewers saw the shoutout.
    cooldown_ends_at: :class:`datetime.datetime`
        When another shoutout can happen.
    target_cooldown_ends_at: :class:`datetime.datetime`
        When the target can have another shoutout towards them.
    """

    __slots__ = (
        "broadcaster",
        "moderator",
        "target",
        "started_at",
        "viewer_count",
        "cooldown_ends_at",
        "target_cooldown_ends_at",
    )

    _dispatches_as = "channel_shoutout_create"
    _required_scopes = ("channel:read:shoutouts", "channel:manage:shoutouts")
    _version = 1
    _event = "channel.shoutout.create"

    def __init__(self, transport: BaseTransport, payload: ChannelShoutoutCreatePayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_", payload)
        self.moderator: PartialUser = _transform_user(transport, "moderator_", payload)
        self.target: PartialUser = _transform_user(transport, "to_broadcaster_", payload)
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])
        self.viewer_count: int = payload["viewer_count"]
        self.cooldown_ends_at: datetime.datetime = parse_timestamp(payload["cooldown_ends_at"])
        self.target_cooldown_ends_at: datetime.datetime = parse_timestamp(payload["target_cooldown_ends_at"])


class ChannelShoutoutReceive(EventData):
    """
    A shoutout receive event. This is created when a shoutout is received, not created.

    Attributes
    -----------
    broadcaster: :class:`~twitchio.PartialUser`
        The broadcaster receiving the shoutout.
    sender: :class:`~twitchio.PartialUser`
        The person sending the shoutout.
    started_at: :class:`datetime.datetime`
        When the shoutout started.
    viewer_count: :class:`int`
        How many viewers saw the shoutout.
    """

    __slots__ = ("broadcaster", "sender", "started_at", "viewer_count")

    _dispatches_as = "channel_shoutout_receive"
    _required_scopes = ("channel:read:shoutouts", "channel:manage:shoutouts")
    _version = 1
    _event = "channel.shoutout.receive"

    def __init__(self, transport: BaseTransport, payload: ChannelShoutoutCreatePayload) -> None:
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_", payload)
        self.sender: PartialUser = _transform_user(transport, "from_broadcaster_", payload)
        self.started_at: datetime.datetime = parse_timestamp(payload["started_at"])
        self.viewer_count: int = payload["viewer_count"]


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
    ChannelPollBegin,
    ChannelPollProgress,
    ChannelPollEnd,
    ChannelPredictionBegin,
    ChannelPredictionProgress,
    ChannelPredictionLock,
    ChannelPredictionEnd,
    ChannelCustomRewardAdd,
    ChannelCustomRewardUpdate,
    ChannelCustomRewardRemove,
    ChannelCustomRewardRedemptionAdd,
    ChannelCustomRewardRedemptionUpdate,
    ChannelShoutoutCreate,
    ChannelShoutoutReceive,
]
