from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO

from pydantic import Field

from .base import BoundObject
from .chat import Chat, ChatAction, User
from .input_file import InputFile
from .markup import InlineKeyboardMarkup, ReplyMarkup
from .media import (
    Animation,
    Audio,
    Contact,
    Document,
    Location,
    PhotoSize,
    Sticker,
    Video,
    Voice,
)
from .payments import Invoice, PreCheckoutQuery, SuccessfulPayment


class MessageEntityType(str, Enum):
    MENTION = "mention"
    BOT_COMMAND = "bot_command"


class MessageEntity(BoundObject):
    type: MessageEntityType | str
    offset: int
    length: int


class MessageId(BoundObject):
    message_id: int


class WebAppData(BoundObject):
    data: str


class Message(BoundObject):
    message_id: int
    from_user: User | None = Field(default=None, alias="from")
    date: int = 0
    chat: Chat
    sender_chat: Chat | None = None
    forward_from: User | None = None
    forward_from_chat: Chat | None = None
    forward_from_message_id: int | None = None
    forward_date: int | None = None
    reply_to_message: Message | None = None
    edit_date: int | None = None
    media_group_id: str | None = None
    text: str | None = None
    entities: list[MessageEntity] | None = None
    animation: Animation | None = None
    audio: Audio | None = None
    document: Document | None = None
    photo: list[PhotoSize] | None = None
    sticker: Sticker | None = None
    video: Video | None = None
    voice: Voice | None = None
    caption: str | None = None
    caption_entities: list[MessageEntity] | None = None
    contact: Contact | None = None
    location: Location | None = None
    new_chat_members: list[User] | None = None
    left_chat_member: User | None = None
    invoice: Invoice | None = None
    successful_payment: SuccessfulPayment | None = None
    web_app_data: WebAppData | None = None
    # the Bale docs type this field inconsistently, so an unexpected shape must never drop
    # the whole update
    reply_markup: InlineKeyboardMarkup | dict[str, Any] | None = None

    @property
    def content_text(self) -> str | None:
        """``text`` for text messages, ``caption`` for media."""
        return self.text if self.text is not None else self.caption

    @property
    def content_type(self) -> str:
        for name in (
            "text", "animation", "audio", "document", "photo", "sticker", "video", "voice",
            "contact", "location", "invoice", "successful_payment", "web_app_data",
            "new_chat_members", "left_chat_member",
        ):  # fmt: skip
            if getattr(self, name, None):
                return name
        return "unknown"

    # --- shortcuts -------------------------------------------------------------------------
    @property
    def file_id(self) -> str | None:
        """``file_id`` of the attached media (largest size for photos)."""
        if self.photo:
            return self.photo[-1].file_id
        for name in ("document", "video", "audio", "voice", "animation", "sticker"):
            media = getattr(self, name, None)
            if media is not None:
                return str(media.file_id)
        return None

    async def answer(
        self, text: str, reply_markup: ReplyMarkup | None = None, *, reply: bool = False
    ) -> Message:
        """Send a message to the same chat (``reply=True`` quotes this message)."""
        return await self.bot.send_message(
            self.chat.id,
            text,
            reply_to_message_id=self.message_id if reply else None,
            reply_markup=reply_markup,
        )

    async def reply(self, text: str, reply_markup: ReplyMarkup | None = None) -> Message:
        return await self.answer(text, reply_markup, reply=True)

    async def answer_photo(
        self,
        photo: InputFile | str,
        caption: str | None = None,
        reply_markup: ReplyMarkup | None = None,
        *,
        reply: bool = False,
    ) -> Message:
        return await self.bot.send_photo(
            self.chat.id, photo, caption, self.message_id if reply else None, reply_markup
        )

    async def answer_document(
        self,
        document: InputFile | str,
        caption: str | None = None,
        reply_markup: ReplyMarkup | None = None,
        *,
        reply: bool = False,
    ) -> Message:
        return await self.bot.send_document(
            self.chat.id, document, caption, self.message_id if reply else None, reply_markup
        )

    async def answer_video(
        self,
        video: InputFile | str,
        caption: str | None = None,
        reply_markup: ReplyMarkup | None = None,
        *,
        reply: bool = False,
    ) -> Message:
        return await self.bot.send_video(
            self.chat.id, video, caption, self.message_id if reply else None, reply_markup
        )

    async def answer_audio(
        self,
        audio: InputFile | str,
        caption: str | None = None,
        reply_markup: ReplyMarkup | None = None,
        *,
        reply: bool = False,
    ) -> Message:
        return await self.bot.send_audio(
            self.chat.id, audio, caption, self.message_id if reply else None, reply_markup
        )

    async def answer_voice(
        self,
        voice: InputFile | str,
        caption: str | None = None,
        reply_markup: ReplyMarkup | None = None,
        *,
        reply: bool = False,
    ) -> Message:
        return await self.bot.send_voice(
            self.chat.id, voice, caption, self.message_id if reply else None, reply_markup
        )

    async def answer_animation(
        self,
        animation: InputFile | str,
        caption: str | None = None,
        reply_markup: ReplyMarkup | None = None,
        *,
        reply: bool = False,
    ) -> Message:
        return await self.bot.send_animation(
            self.chat.id, animation, caption, self.message_id if reply else None, reply_markup
        )

    async def answer_location(
        self, latitude: float, longitude: float, *, reply: bool = False
    ) -> Message:
        return await self.bot.send_location(
            self.chat.id,
            latitude,
            longitude,
            reply_to_message_id=self.message_id if reply else None,
        )

    async def answer_contact(
        self,
        phone_number: str | int,
        first_name: str,
        last_name: str | None = None,
        *,
        reply: bool = False,
    ) -> Message:
        return await self.bot.send_contact(
            self.chat.id,
            phone_number,
            first_name,
            last_name,
            reply_to_message_id=self.message_id if reply else None,
        )

    async def answer_chat_action(self, action: ChatAction | str = ChatAction.TYPING) -> bool:
        return await self.bot.send_chat_action(self.chat.id, action)

    async def edit_text(
        self, text: str, reply_markup: InlineKeyboardMarkup | None = None
    ) -> Message | bool:
        return await self.bot.edit_message_text(self.chat.id, self.message_id, text, reply_markup)

    async def edit_caption(
        self, caption: str | None = None, reply_markup: InlineKeyboardMarkup | None = None
    ) -> Message | bool:
        return await self.bot.edit_message_caption(
            self.chat.id, self.message_id, caption, reply_markup
        )

    async def edit_reply_markup(
        self, reply_markup: InlineKeyboardMarkup | None = None
    ) -> Message | bool:
        return await self.bot.edit_message_reply_markup(self.chat.id, self.message_id, reply_markup)

    async def delete(self) -> bool:
        return await self.bot.delete_message(self.chat.id, self.message_id)

    async def forward(self, chat_id: int | str) -> Message:
        return await self.bot.forward_message(chat_id, self.chat.id, self.message_id)

    async def copy_to(self, chat_id: int | str) -> MessageId:
        return await self.bot.copy_message(chat_id, self.chat.id, self.message_id)

    async def pin(self) -> bool:
        return await self.bot.pin_chat_message(self.chat.id, self.message_id)

    async def unpin(self) -> bool:
        return await self.bot.unpin_chat_message(self.chat.id, self.message_id)

    async def download(self, destination: BinaryIO | str | Path | None = None) -> BinaryIO | None:
        """Download the attached media (see ``Bot.download``)."""
        file_id = self.file_id
        if file_id is None:
            raise ValueError("This message has no downloadable media")
        return await self.bot.download(file_id, destination)


class CallbackQuery(BoundObject):
    id: str
    from_user: User = Field(alias="from")
    message: Message | None = None
    data: str | None = None

    _answered: bool = False

    @property
    def is_answered(self) -> bool:
        return self._answered

    @property
    def is_old_client(self) -> bool:
        """Old Bale clients (``id`` starts with ``1``) cannot receive ``answerCallbackQuery``."""
        return self.id.startswith("1")

    async def answer(self, text: str | None = None, show_alert: bool | None = None) -> bool:
        """Acknowledge the button press. A no-op (returns ``False``) for old clients."""
        self._answered = True
        if self.is_old_client:
            return False
        return await self.bot.answer_callback_query(self.id, text, show_alert)


class Update(BoundObject):
    update_id: int
    message: Message | None = None
    edited_message: Message | None = None
    callback_query: CallbackQuery | None = None
    pre_checkout_query: PreCheckoutQuery | None = None

    @property
    def event_type(self) -> str:
        for name in ("message", "edited_message", "callback_query", "pre_checkout_query"):
            if getattr(self, name) is not None:
                return name
        return "unknown"

    @property
    def event(self) -> Message | CallbackQuery | PreCheckoutQuery | Update:
        if self.message is not None:
            return self.message
        if self.edited_message is not None:
            return self.edited_message
        if self.callback_query is not None:
            return self.callback_query
        if self.pre_checkout_query is not None:
            return self.pre_checkout_query
        return self

    @property
    def unknown_event_types(self) -> dict[str, Any]:
        """Extra update fields not modeled by this version of the library."""
        return self.model_extra or {}


Message.model_rebuild()
