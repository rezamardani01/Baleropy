from __future__ import annotations

from typing import ClassVar

from ..types import (
    ChatAction,
    InlineKeyboardMarkup,
    Message,
    MessageId,
    ReplyMarkup,
)
from ..types.input_file import InputFile
from .base import BaleMethod
from .limits import CallbackText, Caption, Text

ChatId = int | str
FileInput = InputFile | str
MediaInput = InputFile | str


class SendMessage(BaleMethod[Message]):
    __api_method__: ClassVar[str] = "sendMessage"
    __returning__: ClassVar = Message

    chat_id: ChatId
    text: Text
    reply_to_message_id: int | None = None
    reply_markup: ReplyMarkup | None = None


class ForwardMessage(BaleMethod[Message]):
    __api_method__: ClassVar[str] = "forwardMessage"
    __returning__: ClassVar = Message

    chat_id: ChatId
    from_chat_id: ChatId
    message_id: int


class CopyMessage(BaleMethod[MessageId]):
    __api_method__: ClassVar[str] = "copyMessage"
    __returning__: ClassVar = MessageId

    chat_id: ChatId
    from_chat_id: ChatId
    message_id: int


class _SendMedia(BaleMethod[Message]):
    __returning__: ClassVar = Message

    chat_id: ChatId
    caption: Caption | None = None
    reply_to_message_id: int | None = None
    reply_markup: ReplyMarkup | None = None


class SendPhoto(_SendMedia):
    __api_method__: ClassVar[str] = "sendPhoto"
    photo: FileInput


class SendAudio(_SendMedia):
    __api_method__: ClassVar[str] = "sendAudio"
    audio: FileInput


class SendDocument(_SendMedia):
    __api_method__: ClassVar[str] = "sendDocument"
    document: FileInput


class SendVideo(_SendMedia):
    __api_method__: ClassVar[str] = "sendVideo"
    video: FileInput


class SendAnimation(_SendMedia):
    __api_method__: ClassVar[str] = "sendAnimation"
    animation: FileInput


class SendVoice(_SendMedia):
    __api_method__: ClassVar[str] = "sendVoice"
    voice: FileInput


class SendSticker(_SendMedia):
    __api_method__: ClassVar[str] = "sendSticker"
    sticker: FileInput


class SendLocation(BaleMethod[Message]):
    __api_method__: ClassVar[str] = "sendLocation"
    __returning__: ClassVar = Message

    chat_id: ChatId
    latitude: float
    longitude: float
    horizontal_accuracy: float | None = None
    reply_to_message_id: int | None = None
    reply_markup: ReplyMarkup | None = None


class SendContact(BaleMethod[Message]):
    __api_method__: ClassVar[str] = "sendContact"
    __returning__: ClassVar = Message

    chat_id: ChatId
    phone_number: str | int
    first_name: str
    last_name: str | None = None
    reply_to_message_id: int | None = None
    reply_markup: ReplyMarkup | None = None


class SendChatAction(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "sendChatAction"
    __returning__: ClassVar = bool

    chat_id: ChatId
    action: ChatAction | str


class EditMessageText(BaleMethod[Message | bool]):
    __api_method__: ClassVar[str] = "editMessageText"
    __returning__: ClassVar = Message | bool

    chat_id: ChatId
    message_id: int
    text: Text
    reply_markup: InlineKeyboardMarkup | None = None


class EditMessageCaption(BaleMethod[Message | bool]):
    __api_method__: ClassVar[str] = "editMessageCaption"
    __returning__: ClassVar = Message | bool

    chat_id: ChatId
    message_id: int
    caption: Caption | None = None
    reply_markup: InlineKeyboardMarkup | None = None


class EditMessageReplyMarkup(BaleMethod[Message | bool]):
    __api_method__: ClassVar[str] = "editMessageReplyMarkup"
    __returning__: ClassVar = Message | bool

    chat_id: ChatId
    message_id: int
    reply_markup: InlineKeyboardMarkup | None = None


class DeleteMessage(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "deleteMessage"
    __returning__: ClassVar = bool

    chat_id: ChatId
    message_id: int


class AnswerCallbackQuery(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "answerCallbackQuery"
    __returning__: ClassVar = bool

    callback_query_id: str
    text: CallbackText | None = None
    show_alert: bool | None = None
