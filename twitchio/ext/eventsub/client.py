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
from typing import TYPE_CHECKING

from twitchio import Client as _BaseClient

if TYPE_CHECKING:
    from . import models
    from .events import BaseEvent, ChallengeEvent, NotificationEvent, RevocationEvent
    from .transport import BaseTransport

__all__ = ("Client",)


logger = logging.getLogger("twitchio.ext.eventsub.client")


class Client:
    """
    The base EventSub client, which handles incoming eventsub data and dispatches it to your client
    """

    __slots__ = ("_transport", "client")

    def __init__(self, transport: BaseTransport, client: _BaseClient | None = None) -> None:
        self._transport: BaseTransport = transport
        self.client: _BaseClient | None = client

        self._transport._prepare(self)

    async def start(self) -> None:
        await self._transport.start()

    async def stop(self) -> None:
        await self._transport.stop()

    async def _handle_event(self, name: str, event: BaseEvent) -> None:
        if self.client:
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
