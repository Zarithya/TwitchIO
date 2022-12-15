from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Protocol, cast, Type

import aiohttp
import logging
from aiohttp import web
import hashlib
import hmac
from yarl import URL

from . import events
from twitchio.http import Route

if TYPE_CHECKING:
    from .client import Client as _Client
    from .events import BaseEvent, ChallengeEvent, NotificationEvent, RevocationEvent, WebhookMeta as _WebhookMeta
    from .models import AllModels

__all__ = ("BaseTransport", "WebhookTransport", "WebsocketTransport")
logger = logging.getLogger("twitchio.ext.eventsub.transport")

class BaseTransport(Protocol):
    client: _Client

    def __init__(self) -> None:
        ...

    def _prepare(self, client: _Client) -> None:
        self.client = client

    def _pass_event(self, event_data: BaseEvent) -> None:
        t = type(event_data)
        if t is ChallengeEvent:
            event = "challenge"
        elif t is RevocationEvent:
            event = "revocation"
        elif t is NotificationEvent:
            event = "notification"
            event_data = cast(NotificationEvent, event_data)
            asyncio.create_task(self.client._handle_event(event_data.data._dispatches_as, event_data))
        else:
            raise RuntimeError(f"Unknown event type {t}")
        
        asyncio.create_task(self.client._handle_event(event, event_data))

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def transform_event(self, event: Any) -> BaseEvent:
        ...
    
    async def _http(self, route: Route) -> Any:
        raise NotImplementedError

    async def create_subscription(self, topic: AllModels, condition: dict[str, str]) -> Any:
        ...

    async def delete_subscription(self, subscription_id: str) -> Any:
        ...


class WebhookTransport(BaseTransport):
    _message_types: dict[str, Type[BaseEvent]] = {
        "webhook_callback_verification": events.ChallengeEvent,
        "notification": events.NotificationEvent,
        "revocation": events.RevocationEvent,
    }

    def __init__(self, secret: str, callback_url: str | URL, port=4000, **opts) -> None:
        self.app = web.Application()
        self._runner_opts = {"host": "0.0.0.0", "port": port}
        self._url = URL(callback_url)

        self._runner_opts.update(opts)  # overriding the default host *is* possible this way

        router = web.RouteTableDef()
        router.post(self._url.path)(self.request_hook)
        self.app.add_routes(router)

        self.site: web.TCPSite | None = None
        self.secret: str = secret

    async def start(self) -> None:
        """
        Starts listening for webhook messages.
        """
        if self.site and self.site._server:
            await self.stop()

        runner = web.AppRunner(self.app, handle_signals=False)
        self.site = site = web.TCPSite(runner, **self._runner_opts)
        await site.start()

    async def stop(self) -> None:
        """
        Stops listening for webhook messages.
        """
        if not self.site:
            raise RuntimeError("No site running")

        await self.site.stop()
        self.site = None

    async def request_hook(self, request: web.Request) -> web.Response:
        event: BaseEvent | None = await self.transform_event(request)
        if not event:
            return web.Response(status=400)

        err = await self.verify_event(event, await request.text())
        if err:
            return err

        self._pass_event(event)

        if isinstance(event, ChallengeEvent):
            return web.Response(status=200, body=event.challenge)
        
        return web.Response(status=204)

    async def transform_event(self, event: web.Request) -> BaseEvent | None:
        msg_type: str | None = event.headers.get("Twitch-Eventsub-Message-Type")
        if not msg_type:
            return None
        
        try:
            t: Type[BaseEvent] = self._message_types[msg_type]
        except KeyError:
            return None
        
        try:
            return t.from_webhook_event(self, await event.text(), event.headers)
        except:
            raise # FIXME: for dev testing only
            return None
        

    async def verify_event(self, event: BaseEvent, payload: str) -> web.Response | None:
        """
        Verifies the event hash, in compliance with the twitch guidelines.
        This returns any issues found with the request as a Response object, otherwise it returns ``None``.

        Parameters
        -----------
        event: :class:`~twitchio.ext.eventsub.BaseEvent`
            The event received.

        Returns
        --------
        :class:`aiohttp.web.Response` | ``None``
        """
        meta: _WebhookMeta = event.meta # type: ignore
        hmac_message = (meta.message_id + meta._raw_timestamp + payload).encode("utf-8")
        secret = self.secret.encode("utf-8")
        digest = hmac.new(secret, msg=hmac_message, digestmod=hashlib.sha256).hexdigest()

        if not hmac.compare_digest(digest, meta.signature[7:]):
            logger.warning(f"Recieved a message with an invalid signature, discarding.")
            return web.Response(status=400)

    async def create_subscription(self, topic: AllModels, condition: dict[str, str]) -> Any:
        payload = {
            "type": topic._event,
            "version": str(topic._version),
            "condition": condition,
            "transport": {"method": "webhook", "callback": self._url.path, "secret": self.secret},
        }
        route = Route("POST", "eventsub/subscriptions", body=payload, scope=topic._required_scopes and list(topic._required_scopes))
        return await self._http(route)
    
    async def delete_subscription(self, subscription_id: str) -> Any:
        route = Route("DELETE", "eventsub/subscriptions", body=None, parameters=[("id", subscription_id)])
        return await self._http(route)

class WebsocketTransport(BaseTransport):
    ...
