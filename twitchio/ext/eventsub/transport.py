from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Protocol, Type, cast

import aiohttp
from aiohttp import web
from yarl import URL

from twitchio import PartialUser, __version__
from twitchio.http import Route
from twitchio.utils import json_loader

from . import events
from .events import (
    BaseEvent,
    ChallengeEvent,
    KeepaliveEvent,
    NotificationEvent,
    ReconnectEvent,
    RevocationEvent,
    WebhookMeta as _WebhookMeta,
)

if TYPE_CHECKING:
    from .client import Client as _Client
    from .models import AllModels
    from .types.payloads import Condition, HTTPSubscribeResponse, WebsocketMessage

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
        if t is NotificationEvent:
            event = "notification"
            event_data = cast(NotificationEvent, event_data)
            asyncio.create_task(self.client._handle_event(event_data.data._dispatches_as, event_data))
        elif t is KeepaliveEvent:
            event = "keepalive"
        elif t is RevocationEvent:
            event = "revocation"
        elif t is ChallengeEvent:
            event = "challenge"
        elif t is ReconnectEvent:
            event = "reconnect"
        else:
            raise RuntimeError(f"Unknown event type {t}")

        asyncio.create_task(self.client._handle_event(event, event_data))

    async def start(self) -> None:
        ...

    async def stop(self) -> None:
        ...

    async def transform_event(self, event: Any) -> BaseEvent:
        ...

    def _http(self, route: Route) -> Awaitable[Any]:
        return self.client._request(route)

    async def create_subscription(
        self, topic: Type[AllModels], condition: Condition, target: PartialUser | None
    ) -> HTTPSubscribeResponse:
        ...

    async def delete_subscription(self, subscription_id: str) -> bool:
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

        self._stopping: asyncio.Event | None = None

    async def start(self) -> None:
        """
        Starts listening for webhook messages.
        """
        if self.site and self.site._server:
            await self.stop()

        self._stopping = asyncio.Event()

        runner = web.AppRunner(self.app, handle_signals=False)
        self.site = site = web.TCPSite(runner, **self._runner_opts)
        await site.start()

        await self._stopping.wait()

    async def stop(self) -> None:
        """
        Stops listening for webhook messages.
        """
        if not self.site:
            raise RuntimeError("No site running")

        await self.site.stop()
        self.site = None

        if self._stopping is not None:
            self._stopping.set()

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
            raise  # FIXME: for dev testing only
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
        meta: _WebhookMeta = event.meta  # type: ignore
        hmac_message = (meta.message_id + meta._raw_timestamp + payload).encode("utf-8")
        secret = self.secret.encode("utf-8")
        digest = hmac.new(secret, msg=hmac_message, digestmod=hashlib.sha256).hexdigest()

        if not hmac.compare_digest(digest, meta.signature[7:]):
            logger.warning(f"Recieved a message with an invalid signature, discarding.")
            return web.Response(status=400)

    async def create_subscription(self, topic: AllModels, condition: Condition, _) -> HTTPSubscribeResponse:
        payload = {
            "type": topic._event,
            "version": str(topic._version),
            "condition": condition,
            "transport": {"method": "webhook", "callback": self._url.path, "secret": self.secret},
        }
        route = Route(
            "POST",
            "eventsub/subscriptions",
            body=payload,
            scope=topic._required_scopes and list(topic._required_scopes),
        )
        return await self._http(route)

    async def delete_subscription(self, subscription_id: str) -> bool:
        route = Route("DELETE", "eventsub/subscriptions", body=None, parameters=[("id", subscription_id)])
        await self._http(route)
        return True


class WebsocketSubscription:
    __slots__ = ("event", "condition", "subscription_id", "cost", "target")

    def __init__(self, event: AllModels, condition: Condition, target: PartialUser) -> None:
        self.event: AllModels = event
        self.condition: Condition = condition
        self.subscription_id: str | None = None
        self.cost: int | None = None
        self.target: PartialUser = target


class WebsocketShard:
    URL = "wss://eventsub.wss.twitch.tv/ws"

    def __init__(self, transport: WebsocketTransport, user_id: int, connect_kwargs: dict[Any, Any] | None) -> None:
        self.transport: WebsocketTransport = transport
        self._subscriptions: list[WebsocketSubscription] = []
        self.socket: aiohttp.ClientWebSocketResponse | None = None
        self.available_cost = 100
        self._user_id: int = user_id
        self.task: asyncio.Task | None = None
        self.session_id: str | None = None
        self._timeout: int | None = None

        self._connect_kwargs = connect_kwargs or {}

    async def connect(self, reconnect_url: str | None = None) -> None:
        if not self._subscriptions:
            return  # TODO: should this raise?

        # In case you're wondering, no, we don't want to force cancel the pump task if it is running.
        # The pump automatically calls connect if an error occurs, and cancelling the task while its calling connect
        # is basically killing the connect call if thats the case

        async with aiohttp.ClientSession(
            headers={
                "User-Agent": f"TwitchIO {__version__} (https://github.com/TwitchIO/TwitchIO) via aiohttp {aiohttp.__version__}"
            }
        ) as conn:
            self.socket = socket = await conn.ws_connect(reconnect_url or self.URL, **self._connect_kwargs)
            conn.detach()

        welcome = await socket.receive_json(loads=json_loader, timeout=3)
        logger.debug("Received websocket payload: %s", welcome)
        self.session_id = welcome["payload"]["session"]["id"]
        self._timeout = welcome["payload"]["session"]["keepalive_timeout_seconds"]

        logger.info("Created websocket connection with session ID: %s and timeout %s", self.session_id, self._timeout)

        self.task = asyncio.create_task(self.pump(), name=f"Pump-EventSub-{self.session_id}")

        for sub in self._subscriptions:
            await self._subscribe(sub)

    async def disconnect(self) -> None:
        logger.debug("Closing connection to session %s", self.session_id)

        if self.socket and not self.socket.closed:
            await self.socket.close(code=aiohttp.WSCloseCode.GOING_AWAY, message=b"Disconnecting")

        if self.task:
            self.task.cancel()

    async def pump(self):
        while self.socket and not self.socket.closed:
            try:
                msg: str = await self.socket.receive_str(timeout=self._timeout + 1)  # type: ignore

                if not msg:
                    continue

                logger.debug("Received websocket payload: %s", msg)
                event: BaseEvent | None = await self.transport.transform_event(json_loader(msg))
                if not event:
                    continue

                self.transport._pass_event(event)

                if isinstance(event, ReconnectEvent):
                    sock = self.socket
                    self.socket = None
                    await self.connect(event.reconnect_url)
                    await sock.close(code=aiohttp.WSCloseCode.GOING_AWAY, message=b"Reconnecting")
                    return
            
            except TypeError: # happens when we get sent a null frame after getting disconnected
                return

            except asyncio.TimeoutError:
                logger.warning("Socket timeout for eventsub session %s, reconnecting", self.session_id)
                if self.socket and not self.socket.closed:
                    await self.socket.close(code=aiohttp.WSCloseCode.ABNORMAL_CLOSURE, message=b"Timeout reached")

                await self.connect()
                return

            except Exception as e:
                logger.error("Error in the pump task for eventsub session %s", self.session_id, exc_info=e)

        logger.debug(
            "Pump terminated for session %s with close code %s", self.session_id, self.socket and self.socket.close_code
        )

    async def _subscribe(self, subscription: WebsocketSubscription) -> HTTPSubscribeResponse:
        payload = {
            "type": subscription.event._event,
            "version": str(subscription.event._version),
            "condition": subscription.condition,
            "transport": {"method": "websocket", "session_id": self.session_id},
        }
        route = Route(
            "POST",
            "eventsub/subscriptions",
            body=payload,
            scope=subscription.event._required_scopes and list(subscription.event._required_scopes),
            target=subscription.target,
        )
        resp = await self.transport._http(route)
        data = resp["data"][0]
        subscription.cost = data["cost"]
        subscription.subscription_id = data["id"]

        self.available_cost = resp["total_cost"] - resp["max_total_cost"]
        return resp

    async def _unsubscribe(self, subscription: WebsocketSubscription) -> None:
        route = Route(
            "DELETE",
            "eventsub/subscriptions",
            body=None,
            parameters=[("id", subscription.subscription_id)],
            target=subscription.target,
        )
        await self.transport._http(route)

        self._subscriptions.remove(subscription)
        if subscription.cost is not None:
            self.available_cost += subscription.cost

    async def add_subscription(self, subscription: WebsocketSubscription) -> HTTPSubscribeResponse:
        if self.available_cost < 1:
            raise RuntimeError("No remaining slots in this shard")

        self._subscriptions.append(subscription)

        if not self.socket or self.socket.closed:
            await self.connect()

        return await self._subscribe(subscription)


class WebsocketTransport(BaseTransport):
    _message_types = {
        "notification": NotificationEvent,
        "revocation": RevocationEvent,
        "reconnect": ReconnectEvent,
        "session_keepalive": KeepaliveEvent,
    }

    def __init__(self, *, connect_kwargs: dict[str, Any] | None = None) -> None:
        """
        A transport for communicating with eventsub through websockets.
        Pass this to EventSubClient.

        Parameters
        -----------
        connect_kwargs: dict[:class:`str`, Any] | ``None`` = ``None``
            arguments to pass when connecting to the websocket with aiohttp.
            These arguments are passed directly to :func:`aiohttp.ClientSession.ws_connect`
        """
        self.pool: list[WebsocketShard] = []
        self._connect_kwargs = connect_kwargs

    async def start(self) -> None:
        pass  # nothing to do here

    async def stop(self) -> None:
        for shard in self.pool:
            await shard.disconnect()

    async def create_subscription(
        self, topic: AllModels, condition: Condition, target: PartialUser
    ) -> HTTPSubscribeResponse:
        """
        Creates a subscription for an event.

        Parameters
        -----------
        topic: AnyModel
            Pass any model from the :ref:`models<eventsub_models>` to subscribe to that event
        condition: :class:`Condition`
            A dict with any of the Condition keys/values
        target: :class`PartialUser`
            The user to get a token for from the :ref:`token handler<tokens>`

        Raises
        -------
            :class:`ValueError`: No target was passed. Websocket subscriptions require a target user, as a token must be provided.

        Returns
        --------
            dict[:class:`str`, Any]
        """
        if not target:
            raise ValueError("Websocket subscriptions require a target user")

        subscription = WebsocketSubscription(topic, condition, target)
        shard = None

        if not self.pool or sum(shard.available_cost for shard in self.pool if shard._user_id == target.id) < 1:
            shard = WebsocketShard(self, target.id, connect_kwargs=self._connect_kwargs)
            self.pool.append(shard)

        else:
            for s in self.pool:
                if s.available_cost > 1 and s._user_id == target.id:
                    shard = s
                    break

        if shard is None:
            raise RuntimeError(
                "Unable to acquire a shard to assign subscription to. This is an internal error and should be reported"
            )

        return await shard.add_subscription(subscription)

    async def delete_subscription(self, subscription_id: str) -> bool:
        for s in self.pool:
            for sub in s._subscriptions:
                if sub.subscription_id == subscription_id:
                    await s._unsubscribe(sub)
                    return True

        return False

    async def transform_event(self, event: WebsocketMessage) -> BaseEvent | None:
        msg_type: str | None = event["metadata"]["message_type"]
        if not msg_type:
            return None

        try:
            t: Type[BaseEvent] = self._message_types[msg_type]
        except KeyError:
            return None

        try:
            return t.from_websocket_event(self, event)
        except:
            raise  # FIXME: for dev testing only
            return None
