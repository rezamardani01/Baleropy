from __future__ import annotations

from typing import ClassVar

from ..types import File, LabeledPrice, Message, StickerSet, Transaction, Update, User, WebhookInfo
from ..types.base import BaleObject
from ..types.input_file import InputFile
from .base import BaleMethod

ChatId = int | str


# --- updates -----------------------------------------------------------------------------------
class GetUpdates(BaleMethod[list[Update]]):
    __api_method__: ClassVar[str] = "getUpdates"
    __returning__: ClassVar = list[Update]
    offset: int | None = None
    limit: int | None = None
    timeout: int | None = None


class SetWebhook(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "setWebhook"
    __returning__: ClassVar = bool
    url: str


class DeleteWebhook(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "deleteWebhook"
    __returning__: ClassVar = bool


class GetWebhookInfo(BaleMethod[WebhookInfo]):
    __api_method__: ClassVar[str] = "getWebhookInfo"
    __returning__: ClassVar = WebhookInfo


# --- bot / files -------------------------------------------------------------------------------
class GetMe(BaleMethod[User]):
    __api_method__: ClassVar[str] = "getMe"
    __returning__: ClassVar = User


class GetFile(BaleMethod[File]):
    __api_method__: ClassVar[str] = "getFile"
    __returning__: ClassVar = File
    file_id: str


class AskReview(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "askReview"
    __returning__: ClassVar = bool
    user_id: int
    delay_seconds: int


# --- stickers ----------------------------------------------------------------------------------
class InputSticker(BaleObject):
    model_config = BaleObject.model_config | {"arbitrary_types_allowed": True}
    sticker: InputFile | str
    emoji_list: list[str] | None = None


class UploadStickerFile(BaleMethod[File]):
    __api_method__: ClassVar[str] = "uploadStickerFile"
    __returning__: ClassVar = File
    user_id: int
    sticker: InputFile


class CreateNewStickerSet(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "createNewStickerSet"
    __returning__: ClassVar = bool
    user_id: int
    name: str
    title: str
    stickers: list[InputSticker]


class AddStickerToSet(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "addStickerToSet"
    __returning__: ClassVar = bool
    user_id: int
    name: str
    sticker: InputSticker


class GetStickerSet(BaleMethod[StickerSet]):
    __api_method__: ClassVar[str] = "getStickerSet"
    __returning__: ClassVar = StickerSet
    name: str


# --- payments ----------------------------------------------------------------------------------
class SendInvoice(BaleMethod[Message]):
    __api_method__: ClassVar[str] = "sendInvoice"
    __returning__: ClassVar = Message
    chat_id: ChatId
    title: str
    description: str
    payload: str
    provider_token: str
    prices: list[LabeledPrice]
    photo_url: str | None = None
    reply_to_message_id: int | None = None


class CreateInvoiceLink(BaleMethod[str]):
    __api_method__: ClassVar[str] = "createInvoiceLink"
    __returning__: ClassVar = str
    title: str
    description: str
    payload: str
    provider_token: str
    prices: list[LabeledPrice]


class AnswerPreCheckoutQuery(BaleMethod[bool]):
    __api_method__: ClassVar[str] = "answerPreCheckoutQuery"
    __returning__: ClassVar = bool
    pre_checkout_query_id: str
    ok: bool
    error_message: str | None = None


class InquireTransaction(BaleMethod[Transaction]):
    __api_method__: ClassVar[str] = "inquireTransaction"
    __returning__: ClassVar = Transaction
    transaction_id: str
