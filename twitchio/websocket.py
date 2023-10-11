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
import logging
from typing import TYPE_CHECKING, cast, Iterable

import aiohttp

from .tokens import BaseTokenHandler, BaseToken
from .backoff import ExponentialBackoff
from .channel import Channel
from .chatter import PartialChatter
from .exceptions import *
from .limiter import IRCRateLimiter
from .message import Message
from .parser import IRCPayload
from .models import PartialUser

if TYPE_CHECKING:
    from .client import Client
    from .limiter import IRCRateLimiter


logger = logging.getLogger(__name__)

HOST = "wss://irc-ws.chat.twitch.tv:443"


class Websocket:

    __slots__ = (
        "client",
        "ws",
        "join_limiter",
        "heartbeat",
        "token_handler",
        "shard_id",
        "nick",
        "closing",
        "_shard_ready",
        "_keep_alive_task",
        "_channels",
        "_backoff",
        "_shard_target"
    )

    def __init__(
        self,
        token_handler: BaseTokenHandler,
        client: Client,
        limiter: IRCRateLimiter,
        shard_id: str,
        shard_target: str | PartialUser | None,
        heartbeat: float | None = 30.0,
        initial_channels: Iterable[str] | None = None,
        **_,
    ):
        self.client = client

        self.ws: aiohttp.ClientWebSocketResponse | None = None
        self.heartbeat = heartbeat

        self.join_limiter: IRCRateLimiter = limiter

        self.token_handler: BaseTokenHandler = token_handler
        self.shard_id: str = shard_id
        self.nick: str | None = None
        self._channels: set[str] = set(initial_channels or ()) # we keep a list of channels in case we need to reconnect

        self._backoff = ExponentialBackoff()

        self.closing = asyncio.Event()
        self._shard_ready = asyncio.Event()
        self._keep_alive_task: asyncio.Task | None = None
        self._shard_target: str | None = shard_target.name if isinstance(shard_target, PartialUser) else shard_target

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and not self.ws.closed

    async def start_connection(self) -> None:
        while not self.closing.is_set():
            try:
                status = await self._connect()
            except Exception as e:
                self.client.dispatch_listeners("error", e)
                if not self._backoff.is_empty:
                    logger.error(f"Refusing to reconnect shard {self.shard_id} after error when connecting.")
                    return
            else:
                self._shard_ready.clear()
                if self._keep_alive_task:
                    self._keep_alive_task.cancel()
                
                if status:
                    self.client.dispatch_listeners("shard_disconnect", self.shard_id)
                
                continue

    async def _connect(self) -> bool: # bool indicates whether the close was after establishing connection or not
        if self._shard_target is not None:
            token, user = await self.token_handler._client_get_irc_login(self.client, self._shard_target)
            self.nick = user.name
        
        else:
            self.nick = token = None

        async with aiohttp.ClientSession() as session:
            try:
                self.ws = await session.ws_connect(url=HOST, heartbeat=self.heartbeat)
            except Exception as e:
                retry = self._backoff.delay()
                logger.warning(f"Websocket shard {self.shard_id} could not connect. Attempting reconnect in {retry} seconds.", exc_info=e)

                await asyncio.sleep(retry)
                return False

            session.detach()

        self._keep_alive_task = asyncio.create_task(self._keep_alive())

        self.client.dispatch_listeners("shard_connect", self.shard_id)
        
        await self.authentication_sequence(token)

        await asyncio.wait_for(self._keep_alive_task, None)
        return True

    async def _keep_alive(self) -> None:
        while True:
            message: aiohttp.WSMessage = await self.ws.receive()  # type: ignore

            if message.type is aiohttp.WSMsgType.CLOSED:
                if not self.closing:
                    logger.error(f"Websocket was unexpectedly closed. {message.extra or ''}")
                break

            data = message.data

            logger.debug(f"{self.shard_id:<10} IN < {data.rstrip()}")
            self.client.dispatch_listeners("raw_data", data)

            payloads = IRCPayload.parse(data=data)

            for payload in payloads:
                payload: IRCPayload

                if payload.code == 200:
                    event = self.get_event(cast(str, payload.action))
                    asyncio.create_task(event(payload)) if event else None

                elif payload.code == 1:
                    self._shard_ready.set()
                    self.client.dispatch_listeners("shard_ready", self.shard_id)
                    logger.info(f"Shard {self.shard_id} has successful authenticated")


    async def authentication_sequence(self, token: str | None) -> None:
        if token:
            await self.send(f"PASS oauth:{token}", sensitive_text=token)
            await self.send(f"NICK #{self.nick}")
        else:
            await self.send(f"NICK justinfan0000")

        await self.send("CAP REQ :twitch.tv/membership")
        await self.send("CAP REQ :twitch.tv/tags")
        await self.send("CAP REQ :twitch.tv/commands")

        if self._channels:
            await self._join_channels(self._channels)

    async def _join_channels(self, channels: Iterable[str]) -> None:
        await self._shard_ready.wait()

        for channel in channels:
            if cd := self.join_limiter.check_limit():
                await self.join_limiter.wait_for()
            
            await self.send(f"JOIN #{channel.lower()}")

    async def join_channels(self, channels: Iterable[str]) -> None:
        channels = [c.removeprefix("#").lower() for c in channels]
        self._channels.update(channels)

        await self._join_channels(channels)

    async def send(self, message: str, *, sensitive_text: str | None = None) -> None:
        assert self.ws, "There is no websocket"
        message = message.strip("\r\n")
        
        try:
            await self.ws.send_str(f"{message}\r\n")
        except Exception as e:
            logger.exception(f"error sending message: {message}")
            raise
        finally:
            if sensitive_text and not BaseToken.__TOKEN_SHOWS_IN_REPR__:
                message = message.replace(sensitive_text, "...")

            logger.debug(f"{self.shard_id:<10} OUT > {message}")

    def get_event(self, action: str | None):
        if not action:
            return None

        action = action.lower()

        return getattr(self, f"{action}_event")

    async def privmsg_event(self, payload: IRCPayload) -> None:
        logger.debug(
            f"Received PRIVMSG from Twitch: "
            f"channel={payload.channel}, "
            f"chatter={payload.user}, "
            f"content={payload.message}"
        )

        channel = Channel(name=payload.channel, websocket=self)
        chatter = PartialChatter(payload=payload, channel=channel)
        message = Message(payload=payload, channel=channel, chatter=chatter)

        self.client.dispatch_listeners("message", message)

    async def reconnect_event(self, payload: IRCPayload) -> None:
        asyncio.create_task(self._connect())

    async def ping_event(self, payload: IRCPayload) -> None:
        logger.debug("Received PING from Twitch, sending reply PONG.")
        await self.send("PONG :tmi.twitch.tv")

    async def join_event(self, payload: IRCPayload) -> None:
        channel = Channel(name=payload.channel, websocket=self)
        chatter = PartialChatter(payload=payload, channel=channel)  # TODO...

        self.client.dispatch_listeners("join", chatter)

    async def part_event(self, payload: IRCPayload) -> None:
        channel = Channel(name=payload.channel, websocket=self)
        chatter = PartialChatter(payload=payload, channel=channel)  # TODO

        self.client.dispatch_listeners("part", chatter)

    async def cap_event(self, payload: IRCPayload) -> None:
        pass

    async def userstate_event(self, payload: IRCPayload) -> None:
        pass

    async def roomstate_event(self, payload: IRCPayload) -> None:
        pass

    async def whisper_event(self, payload: IRCPayload) -> None:
        logger.debug(f"Received WHISPER from Twitch: sender={payload.user} content={payload.message}")

        chatter = PartialChatter(payload=payload, channel=None)
        message = Message(payload=payload, channel=None, echo=False, chatter=chatter)

        self.client.dispatch_listeners("message", message)

    async def close(self):
        self.closing.set()

        if self.ws:
            await self.ws.close()

        try:
            if self._keep_alive_task:
                self._keep_alive_task.cancel()
        except Exception:
            pass

