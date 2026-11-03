from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..types import CallbackQuery, Chat, ChatType, Message, User
from .base import Filter, FilterResult

if TYPE_CHECKING:
    from ..client.bot import Bot


def _chat_of(event: Any) -> Chat | None:
    if isinstance(event, Message):
        return event.chat
    if isinstance(event, CallbackQuery) and event.message:
        return event.message.chat
    return None


class ChatTypeFilter(Filter):
    """``ChatTypeFilter("private")`` / ``ChatTypeFilter(ChatType.GROUP, "channel")``."""

    def __init__(self, *types: ChatType | str) -> None:
        self.types = {t.value if isinstance(t, ChatType) else t for t in types}

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        chat = _chat_of(event)
        if chat is None:
            return False
        kind = chat.type.value if isinstance(chat.type, ChatType) else chat.type
        return kind in self.types


class IsChatAdmin(Filter):
    """Passes when the author is an owner/administrator of the chat (one API call)."""

    async def __call__(
        self, event: Any, bot: Bot | None = None, event_from_user: User | None = None, **data: Any
    ) -> FilterResult:
        chat = _chat_of(event)
        if bot is None or chat is None or event_from_user is None:
            return False
        member = await bot.get_chat_member(chat.id, event_from_user.id)
        return member.is_admin


class IsMember(Filter):
    """Mandatory-membership check: the author must have joined *every* given chat/channel."""

    def __init__(self, *chat_ids: int | str) -> None:
        if not chat_ids:
            raise ValueError("IsMember needs at least one chat id")
        self.chat_ids = chat_ids

    async def __call__(
        self, event: Any, bot: Bot | None = None, event_from_user: User | None = None, **data: Any
    ) -> FilterResult:
        if bot is None or event_from_user is None:
            return False
        for chat_id in self.chat_ids:
            member = await bot.get_chat_member(chat_id, event_from_user.id)
            if not member.is_joined:
                return False
        return True
