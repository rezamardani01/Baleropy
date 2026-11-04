from __future__ import annotations

from enum import Enum

from .base import BaleObject


class ButtonStyle(str, Enum):
    """Colour of a keyboard button (supported by recent Bale clients).

    ``PRIMARY`` is blue, ``SUCCESS`` green and ``DANGER`` red. Older clients ignore the field and
    show a regular button.
    """

    PRIMARY = "primary"
    SUCCESS = "success"
    DANGER = "danger"


class WebAppInfo(BaleObject):
    url: str


class CopyTextButton(BaleObject):
    text: str


class InlineKeyboardButton(BaleObject):
    model_config = BaleObject.model_config | {"use_enum_values": True}

    text: str
    url: str | None = None
    callback_data: str | None = None
    web_app: WebAppInfo | None = None
    copy_text: CopyTextButton | None = None
    style: ButtonStyle | str | None = None


class InlineKeyboardMarkup(BaleObject):
    inline_keyboard: list[list[InlineKeyboardButton]]


class KeyboardButton(BaleObject):
    model_config = BaleObject.model_config | {"use_enum_values": True}

    text: str
    request_contact: bool | None = None
    request_location: bool | None = None
    web_app: WebAppInfo | None = None
    style: ButtonStyle | str | None = None


class ReplyKeyboardMarkup(BaleObject):
    keyboard: list[list[KeyboardButton]]


class ReplyKeyboardRemove(BaleObject):
    remove_keyboard: bool = True


ReplyMarkup = InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove

__all__ = [
    "ButtonStyle",
    "CopyTextButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "KeyboardButton",
    "ReplyKeyboardMarkup",
    "ReplyKeyboardRemove",
    "ReplyMarkup",
    "WebAppInfo",
]
