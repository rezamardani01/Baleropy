from __future__ import annotations

from enum import Enum
from typing import Any

from ..dispatcher.event.bases import Data, NextHandler
from ..dispatcher.middlewares.base import BaseMiddleware
from .context import FSMContext
from .storage.base import BaseStorage, StorageKey


class FSMStrategy(str, Enum):
    USER_IN_CHAT = "user_in_chat"  # separate state per user in every chat (default)
    CHAT = "chat"  # one shared state for the whole chat
    GLOBAL_USER = "global_user"  # one state per user across all chats


class FSMContextMiddleware(BaseMiddleware):
    """Injects ``state`` (:class:`FSMContext`) and ``raw_state`` into handler data."""

    def __init__(
        self, storage: BaseStorage, strategy: FSMStrategy = FSMStrategy.USER_IN_CHAT
    ) -> None:
        self.storage = storage
        self.strategy = strategy

    def resolve_key(
        self, bot_id: int, chat_id: int | None, user_id: int | None
    ) -> StorageKey | None:
        if chat_id is None and user_id is None:
            return None
        chat_id = chat_id if chat_id is not None else user_id
        user_id = user_id if user_id is not None else chat_id
        assert chat_id is not None and user_id is not None
        if self.strategy is FSMStrategy.CHAT:
            user_id = chat_id
        elif self.strategy is FSMStrategy.GLOBAL_USER:
            chat_id = user_id
        return StorageKey(bot_id=bot_id, chat_id=chat_id, user_id=user_id)

    async def __call__(self, handler: NextHandler, event: Any, data: Data) -> Any:
        chat = data.get("event_chat")
        user = data.get("event_from_user")
        key = self.resolve_key(data["bot"].id, chat.id if chat else None, user.id if user else None)
        if key is not None:
            context = FSMContext(self.storage, key)
            data["state"] = context
            data["raw_state"] = await context.get_state()
        data["fsm_storage"] = self.storage
        return await handler(event, data)
