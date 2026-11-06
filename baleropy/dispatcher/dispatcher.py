from __future__ import annotations

import asyncio
import contextlib
import logging
import random
from typing import Any

from ..client.bot import Bot
from ..exceptions import (
    BaleAPIError,
    BaleNetworkError,
    BaleRetryAfter,
    BaleServerError,
    BaleUnauthorized,
    CancelHandler,
)
from ..fsm.middleware import FSMContextMiddleware, FSMStrategy
from ..fsm.storage.base import BaseStorage
from ..fsm.storage.memory import MemoryStorage
from ..types import Update
from .event.bases import UNHANDLED, Data, ErrorEvent
from .event.observer import EventObserver
from .middlewares.base import wrap_middlewares
from .middlewares.user_context import UserContextMiddleware
from .router import Router

log = logging.getLogger("baleropy.dispatcher")


class Dispatcher(Router):
    """Root router: receives updates (polling / webhook / manual) and feeds them to handlers."""

    def __init__(
        self,
        *,
        name: str | None = None,
        storage: BaseStorage | None = None,
        fsm_strategy: FSMStrategy = FSMStrategy.USER_IN_CHAT,
        **workflow_data: Any,
    ) -> None:
        super().__init__(name=name or "Dispatcher")
        self.storage = storage or MemoryStorage()
        #: extra keyword arguments injected into every handler (``Dispatcher(db=pool)``)
        self.workflow_data: dict[str, Any] = workflow_data
        #: outer middlewares registered here wrap the processing of *every* update
        self.update = EventObserver(self, "update")
        self.update.outer_middleware(UserContextMiddleware())
        self.update.outer_middleware(FSMContextMiddleware(self.storage, fsm_strategy))
        self._stop_event: asyncio.Event | None = None
        self._tasks: set[asyncio.Task[Any]] = set()
        self._semaphore = asyncio.Semaphore(50)

    def __getitem__(self, key: str) -> Any:
        return self.workflow_data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.workflow_data[key] = value

    # --- feeding ---------------------------------------------------------------------------
    async def feed_update(self, bot: Bot, update: Update, **kwargs: Any) -> Any:
        """Process one :class:`Update` and return the handler result (or ``UNHANDLED``)."""
        data: Data = {
            **self.workflow_data,
            **kwargs,
            "bot": bot,
            "dispatcher": self,
            "event_update": update,
        }

        async def listen(upd: Update, ctx: Data) -> Any:
            event_type = upd.event_type
            try:
                return await self.propagate_event(event_type, upd.event, **ctx)
            except CancelHandler:
                return UNHANDLED
            except Exception as error:
                result = await self.propagate_event(
                    "error", ErrorEvent(upd, error), **ctx, exception=error
                )
                if result is UNHANDLED:
                    raise
                return result

        return await wrap_middlewares(self.update.outer_middlewares, listen)(update, data)

    async def feed_raw_update(self, bot: Bot, raw: dict[str, Any], **kwargs: Any) -> Any:
        update = Update.model_validate(raw, context={"bot": bot})
        return await self.feed_update(bot, update, **kwargs)

    # --- polling ---------------------------------------------------------------------------
    async def start_polling(
        self,
        *bots: Bot,
        polling_timeout: int = 30,
        handle_as_tasks: bool = True,
        max_concurrent_updates: int = 50,
        skip_updates: bool = False,
        delete_webhook: bool = True,
        close_bot_session: bool = True,
        backoff: tuple[float, float, float] = (1.0, 5.0, 1.5),
        **kwargs: Any,
    ) -> None:
        """Long-poll ``getUpdates`` for every bot until :meth:`stop_polling` or cancellation.

        ``backoff`` is ``(initial_delay, max_delay, factor)`` used after network failures.
        """
        if not bots:
            raise ValueError("At least one Bot instance is required")
        self._stop_event = asyncio.Event()
        self._semaphore = asyncio.Semaphore(max_concurrent_updates)
        workflow = {**kwargs, "bots": bots}
        await self.emit_startup(dispatcher=self, bot=bots[-1], **self.workflow_data, **workflow)
        try:
            await asyncio.gather(
                *(
                    self._polling(
                        bot,
                        polling_timeout,
                        handle_as_tasks,
                        skip_updates,
                        delete_webhook,
                        backoff,
                        workflow,
                    )
                    for bot in bots
                )
            )
        finally:
            await self._wait_tasks()
            await self.emit_shutdown(
                dispatcher=self, bot=bots[-1], **self.workflow_data, **workflow
            )
            if close_bot_session:
                await asyncio.gather(*(bot.close() for bot in bots), return_exceptions=True)

    def run_polling(self, *bots: Bot, **kwargs: Any) -> None:
        """Blocking helper: ``asyncio.run(start_polling(...))`` that exits quietly on Ctrl+C."""
        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(self.start_polling(*bots, **kwargs))

    async def stop_polling(self) -> None:
        if self._stop_event is None:
            raise RuntimeError("Polling is not running")
        self._stop_event.set()

    async def _polling(
        self,
        bot: Bot,
        timeout: int,
        as_tasks: bool,
        skip_updates: bool,
        delete_webhook: bool,
        backoff: tuple[float, float, float],
        workflow: dict[str, Any],
    ) -> None:
        stop = self._stop_event
        assert stop is not None
        if delete_webhook:
            await bot.delete_webhook()
        offset: int | None = None
        if skip_updates:
            offset = await self._skip_pending(bot)
        delay, max_delay, factor = backoff
        current = delay
        log.info("Polling started for bot %s", bot.id)
        while not stop.is_set():
            fetch = asyncio.create_task(bot.get_updates(offset=offset, limit=100, timeout=timeout))
            waiter = asyncio.create_task(stop.wait())
            try:
                await asyncio.wait({fetch, waiter}, return_when=asyncio.FIRST_COMPLETED)
            except asyncio.CancelledError:
                fetch.cancel()
                waiter.cancel()
                await asyncio.gather(fetch, waiter, return_exceptions=True)
                raise
            if not waiter.done():
                waiter.cancel()
            if not fetch.done():
                fetch.cancel()
                await asyncio.gather(fetch, waiter, return_exceptions=True)
                break
            await asyncio.gather(waiter, return_exceptions=True)
            try:
                updates = fetch.result()
            except BaleUnauthorized:
                log.critical("Bot %s: invalid token, polling stopped", bot.id)
                raise
            except BaleRetryAfter as error:
                await self._sleep(stop, max(error.retry_after, 1))
                continue
            except (BaleNetworkError, BaleServerError) as error:
                sleep_for = current + random.uniform(0, current / 10)  # noqa: S311
                log.warning("Bot %s: %s, retry in %.1fs", bot.id, error, sleep_for)
                await self._sleep(stop, sleep_for)
                current = min(current * factor, max_delay)
                continue
            current = delay
            for update in updates:
                offset = update.update_id + 1
                if as_tasks:
                    task = asyncio.create_task(self._safe_feed(bot, update, workflow))
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)
                else:
                    await self._safe_feed(bot, update, workflow)
        log.info("Polling stopped for bot %s", bot.id)

    async def _skip_pending(self, bot: Bot) -> int | None:
        offset: int | None = None
        while True:
            updates = await bot.get_updates(offset=offset, limit=100, timeout=0)
            if not updates:
                return offset
            offset = updates[-1].update_id + 1

    @staticmethod
    async def _sleep(stop: asyncio.Event, seconds: float) -> None:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=seconds)

    async def _safe_feed(self, bot: Bot, update: Update, workflow: dict[str, Any]) -> None:
        try:
            async with self._semaphore:
                await self.feed_update(bot, update, **workflow)
        except BaleAPIError as error:
            # expected operational errors (blocked bot, no rights...): one line, no traceback
            log.warning("Update %s: %s", update.update_id, error)
        except Exception:
            log.exception("Unhandled error while processing update %s", update.update_id)

    async def _wait_tasks(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
