from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from aiohttp import web
from pydantic import ValidationError

from ..client.bot import Bot
from ..dispatcher.dispatcher import Dispatcher
from ..types import Update

log = logging.getLogger("balegram.webhook")


class SimpleRequestHandler:
    """aiohttp handler that turns Bale webhook POSTs into :meth:`Dispatcher.feed_update` calls.

    Bale sends no secret header, so keep the URL path unguessable (see :func:`secret_path`) or
    pass ``verify`` to authenticate requests yourself (e.g. by source IP or a reverse proxy).
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        bot: Bot,
        handle_in_background: bool = True,
        verify: Callable[[web.Request], bool] | None = None,
        **workflow_data: Any,
    ) -> None:
        self.dispatcher = dispatcher
        self.bot = bot
        self.handle_in_background = handle_in_background
        self.verify = verify
        self.workflow_data = workflow_data
        self._tasks: set[asyncio.Task[Any]] = set()

    def register(self, app: web.Application, path: str) -> None:
        app.router.add_post(path, self.handle)
        app.on_shutdown.append(self._on_shutdown)

    async def _on_shutdown(self, app: web.Application) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def handle(self, request: web.Request) -> web.Response:
        if self.verify is not None and not self.verify(request):
            return web.json_response({"ok": False}, status=403)
        try:
            update = Update.model_validate_json(await request.read(), context={"bot": self.bot})
        except ValidationError:
            return web.json_response({"ok": False, "description": "bad update"}, status=400)
        if self.handle_in_background:
            task = asyncio.create_task(self._feed(update))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        else:
            await self._feed(update)
        return web.json_response({"ok": True})

    async def _feed(self, update: Update) -> None:
        try:
            await self.dispatcher.feed_update(self.bot, update, **self.workflow_data)
        except Exception:
            log.exception("Unhandled error while processing update %s", update.update_id)


def setup_application(app: web.Application, dispatcher: Dispatcher, **kwargs: Any) -> None:
    """Run the dispatcher startup/shutdown hooks with the aiohttp application lifecycle."""

    async def on_startup(app: web.Application) -> None:
        await dispatcher.emit_startup(
            dispatcher=dispatcher, app=app, **dispatcher.workflow_data, **kwargs
        )

    async def on_shutdown(app: web.Application) -> None:
        await dispatcher.emit_shutdown(
            dispatcher=dispatcher, app=app, **dispatcher.workflow_data, **kwargs
        )
        bots = [v for v in kwargs.values() if isinstance(v, Bot)]
        await asyncio.gather(*(bot.close() for bot in bots), return_exceptions=True)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)


def secret_path(prefix: str = "/webhook") -> str:
    """A random, unguessable webhook path such as ``/webhook/Qk3...``."""
    import secrets

    return f"{prefix.rstrip('/')}/{secrets.token_urlsafe(24)}"
