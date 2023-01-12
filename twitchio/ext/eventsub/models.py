from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Protocol, Union

from twitchio import PartialUser
from twitchio.utils import parse_timestamp

if TYPE_CHECKING:
    import datetime

    from .transport import BaseTransport
    from .types.payloads import ChannelUpdate as ChannelUpdatePayload, Images as ImagePayload

__all__ = (
    "ImageLinks",
    "EventData",
    "ChannelUpdate",
    "ChannelFollow"
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
    _required_scopes = None
    _version = 1
    _event = "channel.follow"

    def __init__(self, transport: BaseTransport, payload: Any) -> None:
        self.user: PartialUser = _transform_user(transport, "user_", payload)
        self.broadcaster: PartialUser = _transform_user(transport, "broadcaster_", payload)
        self.followed_at: datetime.datetime = parse_timestamp(payload["followed_at"])


_event_map: dict[str, Type[EventData]] = {t._event: t for t in EventData.__subclasses__()}  # type: ignore
AllModels = Union[
    ChannelUpdate,
    ChannelFollow
]