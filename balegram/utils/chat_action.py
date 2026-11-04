from __future__ import annotations

import asyncio
import contextlib
from types import TracebackType
from typing import TYPE_CHECKING

from ..exceptions import BaleAPIError
from ..types import ChatAction

if TYPE_CHECKING:
    from ..client.bot import Bot


class ChatActionSender:
    """Keeps a chat action ("typing...") alive while a slow block runs.

    >>> async with ChatActionSender.typing(bot, message.chat.id):
    ...     result = await slow_work()
    """

    def __init__(
        self,
        bot: Bot,
        chat_id: int | str,
        action: ChatAction | str = ChatAction.TYPING,
        interval: float = 4.0,
    ) -> None:
        self.bot = bot
        self.chat_id = chat_id
        self.action = action
        self.interval = interval
        self._task: asyncio.Task[None] | None = None

    async def _run(self) -> None:
        while True:
            with contextlib.suppress(BaleAPIError):
                await self.bot.send_chat_action(self.chat_id, self.action)
            await asyncio.sleep(self.interval)

    async def __aenter__(self) -> ChatActionSender:
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    @classmethod
    def typing(cls, bot: Bot, chat_id: int | str, **kwargs: float) -> ChatActionSender:
        return cls(bot, chat_id, ChatAction.TYPING, **kwargs)

    @classmethod
    def upload_photo(cls, bot: Bot, chat_id: int | str, **kwargs: float) -> ChatActionSender:
        return cls(bot, chat_id, ChatAction.UPLOAD_PHOTO, **kwargs)

    @classmethod
    def upload_video(cls, bot: Bot, chat_id: int | str, **kwargs: float) -> ChatActionSender:
        return cls(bot, chat_id, ChatAction.UPLOAD_VIDEO, **kwargs)

    @classmethod
    def record_voice(cls, bot: Bot, chat_id: int | str, **kwargs: float) -> ChatActionSender:
        return cls(bot, chat_id, ChatAction.RECORD_VOICE, **kwargs)

    @classmethod
    def upload_voice(cls, bot: Bot, chat_id: int | str, **kwargs: float) -> ChatActionSender:
        return cls(bot, chat_id, ChatAction.UPLOAD_VOICE, **kwargs)
