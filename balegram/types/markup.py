from __future__ import annotations

from .base import BaleObject


class WebAppInfo(BaleObject):
    url: str


class CopyTextButton(BaleObject):
    text: str


class InlineKeyboardButton(BaleObject):
    text: str
    url: str | None = None
    callback_data: str | None = None
    web_app: WebAppInfo | None = None
    copy_text: CopyTextButton | None = None


class InlineKeyboardMarkup(BaleObject):
    inline_keyboard: list[list[InlineKeyboardButton]]


class KeyboardButton(BaleObject):
    text: str
    request_contact: bool | None = None
    request_location: bool | None = None
    web_app: WebAppInfo | None = None


class ReplyKeyboardMarkup(BaleObject):
    keyboard: list[list[KeyboardButton]]


class ReplyKeyboardRemove(BaleObject):
    remove_keyboard: bool = True


ReplyMarkup = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove

__all__ = [
    "CopyTextButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "KeyboardButton",
    "ReplyKeyboardMarkup",
    "ReplyKeyboardRemove",
    "ReplyMarkup",
    "WebAppInfo",
]
