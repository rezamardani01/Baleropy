from __future__ import annotations

import abc
import asyncio
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, TypeVar

from ...exceptions import (
    BaleAPIError,
    BaleBadRequest,
    BaleForbidden,
    BaleNotFound,
    BaleRetryAfter,
    BaleServerError,
    BaleUnauthorized,
    ClientDecodeError,
)
from ...methods.base import BaleMethod

if TYPE_CHECKING:
    from ..bot import Bot

T = TypeVar("T")

NextRequest = Callable[["Bot", BaleMethod[Any]], Awaitable[Any]]
RequestMiddleware = Callable[[NextRequest, "Bot", BaleMethod[Any]], Awaitable[Any]]

_ERRORS: dict[int, type[BaleAPIError]] = {
    HTTPStatus.BAD_REQUEST: BaleBadRequest,
    HTTPStatus.UNAUTHORIZED: BaleUnauthorized,
    HTTPStatus.FORBIDDEN: BaleForbidden,
    HTTPStatus.NOT_FOUND: BaleNotFound,
    HTTPStatus.TOO_MANY_REQUESTS: BaleRetryAfter,
}


class BaseSession(abc.ABC):
    """Transport layer. Implement :meth:`_send` to plug another HTTP client."""

    def __init__(
        self, timeout: float = 60.0, retry_on_flood: int = 60, max_flood_retries: int = 5
    ) -> None:
        """``retry_on_flood``: sleep and retry when Bale asks to wait at most this many seconds
        (``0`` disables); ``max_flood_retries`` bounds the attempts per request."""
        self.timeout = timeout
        self.retry_on_flood = retry_on_flood
        self.max_flood_retries = max_flood_retries
        self._blocked_until = 0.0
        self._middlewares: list[RequestMiddleware] = []

    def middleware(self, middleware: RequestMiddleware) -> RequestMiddleware:
        """Register an outgoing-request middleware (usable as a decorator)."""
        self._middlewares.append(middleware)
        return middleware

    @abc.abstractmethod
    async def _send(self, bot: Bot, method: BaleMethod[Any]) -> tuple[int, bytes]:
        """Perform the HTTP request and return ``(status, body)``."""

    @abc.abstractmethod
    def stream_content(self, url: str, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        """Async-iterate over a file download."""

    @abc.abstractmethod
    async def close(self) -> None: ...

    async def __call__(self, bot: Bot, method: BaleMethod[T]) -> T:
        handler: NextRequest = self._request
        for middleware in reversed(self._middlewares):
            handler = _wrap(middleware, handler)
        return await handler(bot, method)  # type: ignore[no-any-return]

    async def _request(self, bot: Bot, method: BaleMethod[T]) -> T:
        attempts = 0
        while True:
            # a 429 pauses *every* request of this session, otherwise parallel handlers
            # would all retry at once and trigger the limit again
            delay = self._blocked_until - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            status, body = await self._send(bot, method)
            try:
                return self._parse(bot, method, status, body)
            except BaleRetryAfter as error:
                wait = error.retry_after or 1
                attempts += 1
                if wait > self.retry_on_flood or attempts > self.max_flood_retries:
                    raise
                self._blocked_until = max(self._blocked_until, time.monotonic() + wait)

    @staticmethod
    def _parse(bot: Bot, method: BaleMethod[T], status: int, body: bytes) -> T:
        try:
            payload = json.loads(body)
        except ValueError as error:
            if status >= 500:
                raise BaleServerError(method.__api_method__, f"HTTP {status}", status) from error
            raise ClientDecodeError("Response is not valid JSON", error, body) from error
        if status < 400 and payload.get("ok"):
            return method.build_response(payload.get("result"), bot)
        code = int(payload.get("error_code") or status)
        error_cls = _ERRORS.get(code) or (BaleServerError if code >= 500 else BaleAPIError)
        raise error_cls(
            method.__api_method__,
            payload.get("description") or "unknown error",
            code,
            payload.get("parameters"),
        )

    async def __aenter__(self) -> BaseSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()


def _wrap(middleware: RequestMiddleware, nxt: NextRequest) -> NextRequest:
    async def call(bot: Bot, method: BaleMethod[Any]) -> Any:
        return await middleware(nxt, bot, method)

    return call
