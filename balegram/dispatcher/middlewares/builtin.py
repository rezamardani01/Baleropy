from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from ...exceptions import CancelHandler
from ...types import CallbackQuery
from ..event.bases import Data, NextHandler
from .base import BaseMiddleware

log = logging.getLogger("balegram.middleware")

ThrottledCallback = Callable[[Any, Data], Awaitable[Any]]


class LoggingMiddleware(BaseMiddleware):
    """Logs every event with its handling time (``DEBUG``) and failures (``ERROR``)."""

    def __init__(self, level: int = logging.INFO) -> None:
        self.level = level

    async def __call__(self, handler: NextHandler, event: Any, data: Data) -> Any:
        user = data.get("event_from_user")
        who = user.id if user else "-"
        started = time.perf_counter()
        try:
            return await handler(event, data)
        except Exception:
            log.exception("%s from %s failed", type(event).__name__, who)
            raise
        finally:
            log.log(
                self.level,
                "%s from %s handled in %.1f ms",
                type(event).__name__,
                who,
                (time.perf_counter() - started) * 1000,
            )


class ThrottlingMiddleware(BaseMiddleware):
    """Allows one event per ``rate`` seconds from each user; extra events are dropped.

    ``on_throttled(event, data)`` is awaited the *first* time a user is throttled inside a window,
    so you can answer "slow down" once instead of spamming.
    """

    def __init__(
        self,
        rate: float = 1.0,
        on_throttled: ThrottledCallback | None = None,
        max_tracked: int = 10_000,
    ) -> None:
        self.rate = rate
        self.on_throttled = on_throttled
        self.max_tracked = max_tracked
        self._last: dict[int, float] = {}
        self._warned: set[int] = set()

    def _cleanup(self, now: float) -> None:
        if len(self._last) < self.max_tracked:
            return
        expired = [uid for uid, ts in self._last.items() if now - ts >= self.rate]
        for uid in expired:
            del self._last[uid]
            self._warned.discard(uid)

    async def __call__(self, handler: NextHandler, event: Any, data: Data) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        now = time.monotonic()
        last = self._last.get(user.id)
        if last is not None and now - last < self.rate:
            if self.on_throttled is not None and user.id not in self._warned:
                self._warned.add(user.id)
                await self.on_throttled(event, data)
            raise CancelHandler
        self._cleanup(now)
        self._last[user.id] = now
        self._warned.discard(user.id)
        return await handler(event, data)


class CallbackAnswerMiddleware(BaseMiddleware):
    """Automatically acknowledges callback queries after the handler ran.

    Handlers may still call ``await query.answer(...)`` themselves; queries that were already
    answered are left alone.
    """

    def __init__(self, text: str | None = None, show_alert: bool | None = None) -> None:
        self.text = text
        self.show_alert = show_alert

    async def __call__(self, handler: NextHandler, event: Any, data: Data) -> Any:
        try:
            return await handler(event, data)
        finally:
            if isinstance(event, CallbackQuery) and not event.is_answered:
                try:
                    await event.answer(self.text, self.show_alert)
                except Exception:
                    log.debug("automatic callback answer failed", exc_info=True)
