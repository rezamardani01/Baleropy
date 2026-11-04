from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import TypeAlias

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
ButtonItem: TypeAlias = InlineKeyboardButton | KeyboardButton
ButtonRows: TypeAlias = Sequence[ButtonItem | Sequence[ButtonItem]]
MAX_WIDTH = 8
MAX_BUTTONS = 100


def _build_reply_markup(buttons: ButtonRows | ReplyMarkup | None) -> ReplyMarkup | None:
    if buttons is None or isinstance(
        buttons, (InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove)
    ):
        return buttons
    if not buttons:
        return None

    rows: list[list[ButtonItem]]
    first = buttons[0]
    if isinstance(first, (InlineKeyboardButton, KeyboardButton)):
        flat_row: list[ButtonItem] = []
        for button in buttons:
            if not isinstance(button, (InlineKeyboardButton, KeyboardButton)):
                raise TypeError("Do not mix flat buttons and button rows")
            flat_row.append(button)
        rows = [flat_row]
    else:
        rows = []
        for row in buttons:
            if isinstance(row, (InlineKeyboardButton, KeyboardButton)):
                raise TypeError("Do not mix flat buttons and button rows")
            button_row: list[ButtonItem] = []
            for button in row:
                if not isinstance(button, (InlineKeyboardButton, KeyboardButton)):
                    raise TypeError("Keyboard rows must contain button objects")
                button_row.append(button)
            rows.append(button_row)

    if sum(map(len, rows)) > MAX_BUTTONS:
        raise ValueError(f"A keyboard can hold at most {MAX_BUTTONS} buttons")
    if any(not row for row in rows):
        raise ValueError("Keyboard rows cannot be empty")
    if any(len(row) > MAX_WIDTH for row in rows):
        raise ValueError(f"A keyboard row can hold at most {MAX_WIDTH} buttons")

    first_button = rows[0][0]
    if isinstance(first_button, InlineKeyboardButton):
        inline_rows: list[list[InlineKeyboardButton]] = []
        for row in rows:
            inline_row: list[InlineKeyboardButton] = []
            for button in row:
                if not isinstance(button, InlineKeyboardButton):
                    raise ValueError("Do not mix inline and reply keyboard buttons")
                inline_row.append(button)
            inline_rows.append(inline_row)
        return InlineKeyboardMarkup(inline_keyboard=inline_rows)

    reply_rows: list[list[KeyboardButton]] = []
    for row in rows:
        reply_row: list[KeyboardButton] = []
        for button in row:
            if not isinstance(button, KeyboardButton):
                raise ValueError("Do not mix inline and reply keyboard buttons")
            reply_row.append(button)
        reply_rows.append(reply_row)
    return ReplyKeyboardMarkup(keyboard=reply_rows)


def _build_inline_markup(buttons: ButtonRows | None) -> InlineKeyboardMarkup | None:
    markup = _build_reply_markup(buttons)
    if markup is not None and not isinstance(markup, InlineKeyboardMarkup):
        raise ValueError("Message editing only supports inline keyboard buttons")
    return markup


__all__ = [
    "ButtonStyle",
    "ButtonItem",
    "ButtonRows",
    "CopyTextButton",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "KeyboardButton",
    "ReplyKeyboardMarkup",
    "ReplyKeyboardRemove",
    "ReplyMarkup",
    "WebAppInfo",
]
