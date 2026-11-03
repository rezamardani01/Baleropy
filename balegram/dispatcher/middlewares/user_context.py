from __future__ import annotations

from typing import Any

from ...types import CallbackQuery, Chat, Message, PreCheckoutQuery, Update, User
from ..event.bases import Data, NextHandler
from .base import BaseMiddleware


class UserContextMiddleware(BaseMiddleware):
    """Adds ``event_from_user`` and ``event_chat`` to the handler data of every update."""

    async def __call__(self, handler: NextHandler, event: Any, data: Data) -> Any:
        if isinstance(event, Update):
            user: User | None = None
            chat: Chat | None = None
            inner = event.event
            if isinstance(inner, Message):
                user, chat = inner.from_user, inner.chat
            elif isinstance(inner, CallbackQuery):
                user = inner.from_user
                chat = inner.message.chat if inner.message else None
            elif isinstance(inner, PreCheckoutQuery):
                user = inner.from_user
            if user is not None:
                data["event_from_user"] = user
            if chat is not None:
                data["event_chat"] = chat
        return await handler(event, data)
