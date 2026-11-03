from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import aiohttp

from ...exceptions import BaleNetworkError
from ...methods.base import BaleMethod
from .base import BaseSession

if TYPE_CHECKING:
    from ..bot import Bot


class AiohttpSession(BaseSession):
    def __init__(
        self,
        timeout: float = 60.0,
        retry_on_flood: int = 0,
        proxy: str | None = None,
        connector: aiohttp.BaseConnector | None = None,
    ) -> None:
        super().__init__(timeout, retry_on_flood)
        self.proxy = proxy
        self._connector = connector
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(connector=self._connector)
        return self._session

    async def _send(self, bot: Bot, method: BaleMethod[Any]) -> tuple[int, bytes]:
        session = await self._get_session()
        url = bot.server.api_url(bot.token, method.__api_method__)
        data, files = method.build_request()
        kwargs: dict[str, Any] = {}
        if files:
            form = aiohttp.FormData(quote_fields=False)
            for key, value in data.items():
                form.add_field(key, _form_value(value))
            for key, file in files.items():
                form.add_field(key, await file.read(), filename=file.filename)
            kwargs["data"] = form
        else:
            kwargs["json"] = data
        # the library timeout of getUpdates must cover server-side long polling
        long_poll = getattr(method, "timeout", None) or 0
        timeout = aiohttp.ClientTimeout(total=self.timeout + float(long_poll))
        try:
            async with session.post(url, timeout=timeout, proxy=self.proxy, **kwargs) as response:
                return response.status, await response.read()
        except asyncio.TimeoutError as error:
            raise BaleNetworkError(f"Request timeout ({method.__api_method__})") from error
        except aiohttp.ClientError as error:
            raise BaleNetworkError(f"{type(error).__name__}: {error}") from error

    async def stream_content(self, url: str, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        session = await self._get_session()
        try:
            async with session.get(url, proxy=self.proxy) as response:
                response.raise_for_status()
                async for chunk in response.content.iter_chunked(chunk_size):
                    yield chunk
        except aiohttp.ClientError as error:
            raise BaleNetworkError(f"{type(error).__name__}: {error}") from error

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None


def _form_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
