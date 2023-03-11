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
import re

USER_REGEX = re.compile(r"user-type=*\S*.:(?P<USER>.*?)!\S*")
CHANNEL_REGEX = re.compile(r"tmi\.twitch\.tv [A-Z()]* #(?P<CHANNEL>\S*)")

TMI = ":tmi.twitch.tv"


class IRCPayload:
    """Parsed IRC Payload object.

    Attributes
    ----------
    raw: str
        The raw data received via Twitch Websocket.
    code: int
        The code received via Twitch. If no code was received this will be 200 to denote success.
    tags: dict
        The tags associated with the IRC payload. Could be an empty dict if no tags were received.
    action: Optional[:class:`str`]
        The IRC action. E.g PRIVMSG or ROOMSTATE. Could be None.
    message: Optional[:class:`str`]
        The message associated with the IRC payload. Could be None.
    channel: Optional[:class:`str`]
        The channel this payload was received in. Could be None.
    user: Optional[:class:`str`]
        The user this payload related to. Could be None.
    names: Optional[:class:`list`]
        A list of names received with JOIN/Code 353. Could be None.
    badges: :class:`dict`
        The badges received via tags. Could be an empty dict if no badges were received.
    """

    def __init__(
        self,
        *,
        raw: str,
        code: int,
        tags: dict,
        action: str | None = None,
        message: str | None = None,
        channel: str | None = None,
        user: str | None = None,
        names: list | None = None,
    ):
        self.raw = raw
        self.code = code
        self.action = action
        self.message = message
        self.channel = channel
        self.user = user
        self.names = names

        self.badges = tags.get("badges", {})
        self.tags = tags

        if tags == {"badges": {}}:
            self.tags = {}

    @classmethod
    def parse(cls, data: str) -> list:
        return [cls._parse(data) for data in data.split("\n")] if data else []

    @classmethod
    def _parse(cls, data: str):
        try:
            channel = CHANNEL_REGEX.search(data)
            if channel:
                channel = channel["CHANNEL"]
        except (TypeError, KeyError):
            channel = None

        parts = data.split(" ")

        tags: dict[str, dict[str, str] | str | int] = {"badges": {}}

        try:
            parts.remove(TMI)
        except ValueError:
            pass

        zero = parts[0]

        try:
            code = int(zero)
        except ValueError:
            try:
                code = int(parts[1])
            except (IndexError, ValueError):
                code = 200

        try:
            user = USER_REGEX.search(data)
            if user:
                user = user["USER"]
        except (TypeError, KeyError):
            user = None

        if zero.startswith("PING"):
            action = "PING"

        elif zero.startswith("@"):
            action = parts[2] if user else parts[1]

            zero = zero.lstrip("@")

            raw_tags = zero.split(";")
            for tag in raw_tags:
                key, value = tag.split("=", 1)

                if key == "badges" and value:
                    badges = {}

                    raw_badges = value.split(",")
                    for badge in raw_badges:
                        bkey, bvalue = badge.split("/")

                        badges[bkey] = bvalue

                    tags[key] = badges
                    continue

                tags[key] = value

        elif zero.startswith(":"):
            action = parts[1]

        else:
            action = zero

        if code == 353:
            names = data.split(":")[-1].split()
            message = None
            user = parts[2]
            channel = parts[4].lstrip("#")
        else:
            names = None
            message = data.split(":")[-1]

        if channel and "PRIVMSG" in data:
            message = data.split(f"{channel} :")[-1]

        if code != 200:
            action = None

        return cls(
            raw=data, code=code, action=action, message=message, channel=channel, user=user, tags=tags, names=names
        )
