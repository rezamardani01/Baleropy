from __future__ import annotations

from enum import Enum

from pydantic import Field

from .base import BoundObject
from .chat import Chat, User
from .markup import InlineKeyboardMarkup
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
    reply_markup: InlineKeyboardMarkup | None = None

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


class CallbackQuery(BoundObject):
    id: str
    from_user: User = Field(alias="from")
    message: Message | None = None
    data: str | None = None


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
    def event(self) -> Message | CallbackQuery | PreCheckoutQuery | None:
        return getattr(self, self.event_type, None)


Message.model_rebuild()
