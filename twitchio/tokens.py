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

import time
from typing import TYPE_CHECKING

import logging
import aiohttp
from typing_extensions import Self
from yarl import URL

from .exceptions import InvalidToken, RefreshFailure, NoTokenAvailable
from .utils import json_loader, maybe_coro

if TYPE_CHECKING:
    from .client import Client
    from .http import HTTPHandler
    from .models import PartialUser, User

__all__ = ("BaseToken", "Token", "BaseTokenHandler", "SimpleTokenHandler", "IRCTokenHandler")

VALIDATE_URL = URL("https://id.twitch.tv/oauth2/validate")
REFRESH_URL = URL("https://id.twitch.tv/oauth2/refresh")

logger = logging.getLogger(__name__)

class BaseToken:
    """
    A base token container.
    This base class takes an access token, and does no validation on it before allowing it to be used for requests.
    This is useful for passing app access tokens.

    .. container:: operations

        .. describe:: x == y

            Checks if the token is equal to another.
        
        .. describe:: x != y

            Checks if the token is not equal to another.
        
        .. describe:: str(x)

            Returns the token.

        .. describe:: hash(x)

            Returns the hash of the access token

    Attributes
    -----------
    access_token: :class:`str`
        The access token to use.

    .. versionadded:: 3.0
    """

    __TOKEN_SHOWS_IN_REPR__ = True

    def __init__(self, access_token: str) -> None:
        self.access_token: str = access_token
    
    def __eq__(self, other: object) -> bool:
        return (isinstance(other, BaseToken) and other.access_token == self.access_token) or (isinstance(other, str) and other == self.access_token)
    
    def __hash__(self) -> int:
        return hash(self.access_token)

    def __str__(self) -> str:
        return self.access_token
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} access_token={self.access_token if BaseToken.__TOKEN_SHOWS_IN_REPR__ else '...'}>"

    async def get(self, http: HTTPHandler, handler: BaseTokenHandler, session: aiohttp.ClientSession) -> str:
        """|coro|
        Ensures the token is still within the validation period, and then returns the current access token.

        Parameters
        -----------
        http: :class:`~twitchio.http.HTTPHandler`
            The HTTP session
        handler: :class:`BaseTokenHandler`
            The handler passed to your Client/Bot
        session: :class:`~aiohttp.ClientSession`
            The session to use for validating the token

        Raises
        -------
        :error:`~twitchio.InvalidToken`
            This token is invalid

        Returns
        --------
        :class:`str`
            The access token
        """
        return self.access_token


class Token(BaseToken):
    """
    A container around user OAuth tokens.
    This class will automatically ensure tokens are valid before allowing the library to use them, and will refresh tokens if possible.

    .. container:: operations

        .. describe:: x == y

            Checks if the token is equal to another.
        
        .. describe:: x != y

            Checks if the token is not equal to another.
        
        .. describe:: str(x)

            Returns the token.

        .. describe:: hash(x)

            Returns the hash of the access token

    .. versionadded:: 3.0

    Attributes
    -----------
    access_token: :class:`str`
        The token itself. This should **not** be prefixed with ``oauth:``!
    refresh_token: Optional[:class:`str`]
        The reresh token associated with the access token. This is not useful unless you have passed ``client_secret`` to your :class:`~twitchio.Client`/:class:`~twitchio.ext.commands.Bot`

    """

    def __init__(self, access_token: str, refresh_token: str | None = None) -> None:
        super().__init__(access_token)
        self.refresh_token: str | None = refresh_token
        self._user: PartialUser | None = None
        self._scopes: list[str] = []
        self._last_validation: float | None = None
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} user={self._user} access_token={self.access_token if BaseToken.__TOKEN_SHOWS_IN_REPR__ else '...'} " \
            f"refresh_token={self.refresh_token if BaseToken.__TOKEN_SHOWS_IN_REPR__ else '...'} scopes={self._scopes}>"

    async def refresh(self, handler: BaseTokenHandler, session: aiohttp.ClientSession) -> None:
        """|coro|
        Refreshes the access token, if a refresh token has been provided.
        If one hasn't been provided, this will raise :class:`~twitchio.InvalidToken`.

        Parameters
        -----------
        handler: :class:`BaseTokenHandler`
            The token handler being used to refresh this token. This should be the same handler that was passed to your Client/Bot
        session: :class:`~aiohttp.ClientSession`
            The session to use to refresh the token

        Raises
        -------
        :error:`~twitchio.InvalidToken`
            The refresh token is missing or invalid.
        :error:`~twitchio.RefreshFailure`
            The token could not be refreshed.
        """
        client_id, client_secret = await handler.get_client_credentials()

        if not client_id or not client_secret:
            raise RefreshFailure("Cannot refresh user tokens without a client ID and client secret present")

        logger.debug("Refreshing token for %s", self._user)

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        async with session.get(REFRESH_URL, data=payload) as resp:
            data = await resp.json(loads=json_loader)
            if data["status"] == 401:
                raise RefreshFailure(data["message"])

            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]

    async def validate(self, http: HTTPHandler, handler: BaseTokenHandler, session: aiohttp.ClientSession) -> None:
        """|coro|
        Validates the token, caching information on how this token is to be used.
        Tokens must be validated every hour, as per the `dev docs <https://dev.twitch.tv/docs/authentication/validate-tokens>`_.

        Parameters
        -----------
        http: :class:`~twitchio.http.HTTPManager
            The HTTP session
        handler: :class:`BaseTokenHandler`
            The handler that was passed to your Client/Bot
        session: :class:`~aiohttp.ClientSession`
            The session to use for validating the token

        Raises
        -------
        :error:`~twitchio.InvalidToken`
            This token is invalid
        """

        async with session.get(VALIDATE_URL, headers={"Authorization": f"OAuth {self.access_token}"}) as resp:
            if resp.status == 401:
                logger.debug("Token %s did not pass validation", self.access_token if BaseToken.__TOKEN_SHOWS_IN_REPR__ else '...')
                try:
                    await self.refresh(handler, session)
                except Exception as e:
                    raise InvalidToken("The token is invalid, and a new one could not be generated") from e

            data = await resp.json(loads=json_loader)

        if "login" not in data:
            raise InvalidToken("The token provided is an app access token. These cannot be used with the Token object")

        from .models import PartialUser

        self._scopes = data["scopes"]
        self._user = PartialUser(http, data["user_id"], data["login"])

    async def get(self, http: HTTPHandler, handler: BaseTokenHandler, session: aiohttp.ClientSession) -> str:
        """|coro|
        Ensures the token is still within the validation period, and then returns the current access token.

        Parameters
        -----------
        http: :class:`~twitchio.http.HTTPHandler`
            The HTTP session
        handler: :class:`BaseTokenHandler`
            The handler passed to your Client/Bot
        session: :class:`~aiohttp.ClientSession`
            The session to use for validating the token

        Raises
        -------
        :error:`~twitchio.InvalidToken`
            This token is invalid

        Returns
        --------
        :class:`str`
            The access token
        """
        if not self._last_validation or self._last_validation < (time.time() - 3600):
            await self.validate(http, handler, session)

        return self.access_token

    def has_scope(self, scope: str) -> bool | None:
        """
        A helper function which determines whether the given token has a given scope or not.
        If the token has not previously been validated, this function will return ``None``

        Parameters
        -----------
        scope: :class:`str`
            The scope to check this token for

        Returns
        --------
        Optional[:class:`bool`]
            Whether this token has the scope or not
        """
        return scope in self._scopes if self._scopes else None


class BaseTokenHandler:
    """
    A base class to manage user tokens.
    
    This class is designed to be subclassed.
    The library will aggressively cache user tokens, and will only call your code when a token cannot be found in the cache.

    A short example of a subclassed token handler:

    .. code-block:: python

        import os
        import json
        import twitchio
        
        class MyTokenHandler(twitchio.BaseTokenHandler):
            def __init__(self):
                # While we recommend storing tokens in an actual database, this will suffice for the example.
                # A JSON file will suffice fine for a personal bot, however if you wish to expand to support more users,
                # using a JSON file is an extremely bad idea.

                # This example JSON file stores tokens in a dict of user_id: [token, refresh_token]. It does not take scopes into account, 
                # which you should probably do. 

                with open("tokens.json") as file:
                    self.user_tokens = json.load(file)
                
                super().__init__()
                
            def get_client_credentials(self): # can be async
                return os.getenv("CLIENT_ID"), os.getenv("CLIENT_SECRET")
            
            def get_irc_token(self): # can be async
                return twitchio.Token(os.getenv("IRC_TOKEN"))
            
            async def get_user_token(self, user: twitchio.PartialUser, scopes: tuple[str]): # can be sync
                user_id = user.id
                if user_id not in self.user_tokens:
                    raise RuntimeError("User not found :(")
                
                tokens = self.user_tokens[user_id]
                return twitchio.Token(tokens[0], refresh_token=tokens[1])
    """
    client: Client

    __oauth_url__ = "https://id.twitch.tv/oauth2/token"

    def __init__(self) -> None:
        self.__cache: dict[User | PartialUser, set[Token]] = {}

    def _post_init(self, client: Client) -> Self:
        self.client = client
        return self
    
    def _evict(self, token: Token) -> bool:
        # evicts a token from the cache
        user = token._user

        if not user:
            return False # cant be in cache if theres no user yet
        
        try:
            self.__cache[user].remove(token)
            return True
        except:
            return False
    
    async def _get_token_from_credentials(self) -> BaseToken | None:
        # this does not raise if no client secret is found, only if an http error occurs
        client_id, client_secret = await maybe_coro(self.get_client_credentials)

        if not (client_id and client_secret):
            return None
        
        query = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        async with self.client._http._session.post(URL(self.__oauth_url__).with_query(query)) as resp: # type: ignore
            resp.raise_for_status() # this may hard crash, but thats intentional, as this indicates a failure to acquire the proper tokens
            data = await resp.json(loads=json_loader)
            return BaseToken(data["access_token"])

    async def _client_get_user_token(
        self, http: HTTPHandler, user: User | PartialUser, scope: tuple[str], *, no_cache: bool = False
    ) -> Token:
        if not no_cache and user in self.__cache:
            if not self.__cache[user]:
                del self.__cache[user]

            elif scope:
                for token in self.__cache[user]:
                    if scope in token._scopes:
                        return token

            else:
                return next(iter(self.__cache[user]))

        try:
            token = await self.get_user_token(user, scope)
            if not http._session:
                await http.prepare()

            await token.validate(http, self, http._session)  # type: ignore
        except Exception as e:
            # TODO fire error handlers
            raise

        if user not in self.__cache:
            self.__cache[user] = set()

        self.__cache[user].add(token)
        return token

    async def _client_get_client_token(self) -> BaseToken:
        try:
            t = await maybe_coro(self.get_client_token)
        except Exception as e:
            # TODO fire error handlers
            raise
        
        if t:
            return t
        
        token = await self._get_token_from_credentials()

        if not token:
            raise NoTokenAvailable(f"No token was returned from {self.__class__.__name__}.get_client_token, and one could not be generated.")
                
        return token

    async def _client_get_irc_login(self, client: Client, shard_id: int) -> tuple[str, PartialUser]:
        try:
            token = await maybe_coro(self.get_irc_token, shard_id)
        except Exception as e:
            raise  # TODO fire error handlers

        if not client._http._session:
            await client._http.prepare()

        resp = await token.get(client._http, self, client._http._session)  # type: ignore

        if not token.has_scope("chat:login") and not token.has_scope("chat:read"):
            raise InvalidToken(
                f"The token given for user {token._user} does not have the chat:login or chat:read scope."
            )

        return resp, token._user  # type: ignore
        
    async def get_client_token(self) -> BaseToken:
        """|maybecoro|
        Method to be overriden in a subclass.
        This should return a client token (generated with client id and client secret). If not implemented,
        the library will attempt to generate one with the credentials returned from :meth:`~.get_client_credentials`.
        
        .. warning::

            If the library is unable to fetch any client token, it will hard crash.
        
        Returns
        --------
        :class:`BaseToken`
            The client token.
        """
        raise NotImplementedError

    async def get_client_credentials(self) -> tuple[str, str | None]:
        """|maybecoro|
        Method to be overriden in a subclass.
        This should return a :class:`tuple` of (client id, client secret).
        The client secret is not required, however the client id is required to make requests to the twitch API.
        The client secret is required to automatically refresh user tokens when they expire, however it is not required to access the twitch API.
        """
        raise NotImplementedError

    async def get_irc_token(self, shard_id: int) -> Token:
        """|maybecoro|
        Method to be overriden in a subclass.
        This should return a :class:`Token` containing an OAuth token with the ``chat:login`` scope.

        Parameters
        -----------
        shard_id: :class:`int`
            The shard that is attempting to connect.

        Returns
        -------
        :class:`Token`
            The token with which to connect
        """
        raise NotImplementedError
    
    async def get_user_token(self, user: User | PartialUser, scopes: tuple[str]) -> Token:
        """|maybecoro|
        Method to be overriden in a subclass.
        This function receives a user and a list of scopes that the request needs any one of to make the request.
        It should return a :class:`Token` object.

        .. note::
            It is a good idea to pass a refresh token if you have one available,
            the library will automatically handle refreshing tokens if one is provided.

        Parameters
        -----------
        user: Union[:class:`~twitchio.User`, :class:`~twitchio.PartialUser`]
            The user that a token is expected for.
        scopes: tuple[:class:`str`]
            A list of scopes that the endpoint needs one of. Any one or more of the scopes must be present on the returned token to successfully make the request

        Returns
        --------
        :class:`Token`
            The token for the associated user.
        """
        raise NotImplementedError


class SimpleTokenHandler(BaseTokenHandler):
    """
    A simple token handler, it takes an access token (and optionally a refresh token), and uses that access token for every request.
    You may also pass a client_token, which will be used for all requests that do not use a user token.
    If not provided, the user access token will be used for all requests.

    Attributes
    -----------
    user_token: :class:`Token`
        The token to use for all requests
    client_token: Optional[:class:`str`]
        The token to use for all client credential requests (requests that don't require user authorization)
    client_id: :class:`str`
        The client id associated with all tokens
    client_secret: Optional[:class:`str`]
        The client secret associated with the client id. This can be used to refresh tokens if they expire
    """

    def __init__(
        self,
        access_token: str,
        client_id: str,
        refresh_token: str | None = None,
        client_token: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        super().__init__()
        self.user_token = Token(access_token, refresh_token)
        self.client_token = client_token
        self.client_id: str = client_id
        self.client_secret: str | None = client_secret

    async def get_user_token(self, user: User | PartialUser, scopes: tuple[str]) -> Token:
        return self.user_token

    async def get_client_token(self) -> BaseToken:
        return BaseToken(self.client_token) if self.client_token else BaseToken(self.user_token.access_token)

    async def get_client_credentials(self) -> tuple[str, str | None]:
        return self.client_id, self.client_secret

    async def get_irc_token(self, shard_id: int) -> Token:
        return self.user_token


class IRCTokenHandler(BaseTokenHandler):
    """
    A token handler to be used for IRC-only connections.
    You will not be able to make API calls while using this token handler.
    This handler does not accept a Client ID, or refresh token.
    If you want functionality such as refreshing your token, use the :class:`SimpleTokenHandler`, or subclass :class:`BaseTokenHandler`

    Attributes
    -----------
    user_token: :class:`Token`
        The token to use for all requests
    """

    def __init__(self, access_token: str) -> None:
        super().__init__()
        self.user_token = Token(access_token)

    async def get_client_credentials(self) -> tuple[str, str | None]:
        return None, None  # type: ignore

    async def get_irc_token(self, shard_id: int) -> Token:
        return self.user_token
