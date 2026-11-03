from __future__ import annotations

import abc
import json
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

    def __init__(self, timeout: float = 60.0, retry_on_flood: int = 0) -> None:
        self.timeout = timeout
        self.retry_on_flood = retry_on_flood
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
        while True:
            status, body = await self._send(bot, method)
            try:
                return self._parse(bot, method, status, body)
            except BaleRetryAfter as error:
                if error.retry_after and error.retry_after <= self.retry_on_flood:
                    import asyncio

                    await asyncio.sleep(error.retry_after)
                    continue
                raise

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
