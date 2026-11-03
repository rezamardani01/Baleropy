from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Generic, TypeVar

from ..filters.callback_data import CallbackData
from ..types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

B = TypeVar("B", InlineKeyboardButton, KeyboardButton)

MAX_WIDTH = 8
MAX_BUTTONS = 100


class _KeyboardBuilder(Generic[B]):
    def __init__(self, buttons: Iterable[Iterable[B]] | None = None) -> None:
        self._rows: list[list[B]] = [list(row) for row in buttons or []]

    def __len__(self) -> int:
        return sum(len(row) for row in self._rows)

    def __iter__(self) -> Iterator[B]:
        for row in self._rows:
            yield from row

    def _check(self, count: int) -> None:
        if len(self) + count > MAX_BUTTONS:
            raise ValueError(f"A keyboard can hold at most {MAX_BUTTONS} buttons")

    def add(self, *buttons: B) -> Any:
        """Append buttons to the last row (a new row starts after ``MAX_WIDTH`` buttons)."""
        self._check(len(buttons))
        for button in buttons:
            if not self._rows or len(self._rows[-1]) >= MAX_WIDTH:
                self._rows.append([])
            self._rows[-1].append(button)
        return self

    def row(self, *buttons: B, width: int = MAX_WIDTH) -> Any:
        """Append the buttons as new row(s) of at most ``width`` buttons."""
        if not 1 <= width <= MAX_WIDTH:
            raise ValueError(f"width must be between 1 and {MAX_WIDTH}")
        self._check(len(buttons))
        for start in range(0, len(buttons), width):
            self._rows.append(list(buttons[start : start + width]))
        return self

    def adjust(self, *sizes: int, repeat: bool = False) -> Any:
        """Re-flow every button into rows of the given sizes.

        With ``repeat`` the sizes cycle; otherwise the last size keeps being used.
        """
        if not sizes or any(not 1 <= s <= MAX_WIDTH for s in sizes):
            raise ValueError(f"sizes must be between 1 and {MAX_WIDTH}")
        flat = list(self)
        self._rows = []
        position, index = 0, 0
        while position < len(flat):
            if index < len(sizes):
                size = sizes[index]
            else:
                size = sizes[index % len(sizes)] if repeat else sizes[-1]
            self._rows.append(flat[position : position + size])
            position += size
            index += 1
        return self

    def attach(self, other: _KeyboardBuilder[B]) -> Any:
        """Append every row of another builder."""
        self._check(len(other))
        self._rows.extend(list(row) for row in other._rows)
        return self

    def export(self) -> list[list[B]]:
        return [list(row) for row in self._rows]


class InlineKeyboardBuilder(_KeyboardBuilder[InlineKeyboardButton]):
    """``InlineKeyboardBuilder().button(text="Yes", callback_data="y").as_markup()``"""

    def button(
        self,
        text: str,
        *,
        callback_data: str | CallbackData | None = None,
        url: str | None = None,
        web_app: WebAppInfo | str | None = None,
        copy_text: CopyTextButton | str | None = None,
    ) -> InlineKeyboardBuilder:
        actions = [a for a in (callback_data, url, web_app, copy_text) if a is not None]
        if len(actions) > 1:
            raise ValueError("Use only one of callback_data, url, web_app, copy_text")
        if isinstance(callback_data, CallbackData):
            callback_data = callback_data.pack()
        if isinstance(web_app, str):
            web_app = WebAppInfo(url=web_app)
        if isinstance(copy_text, str):
            copy_text = CopyTextButton(text=copy_text)
        return self.add(  # type: ignore[no-any-return]
            InlineKeyboardButton(
                text=text,
                callback_data=callback_data,
                url=url,
                web_app=web_app,
                copy_text=copy_text,
            )
        )

    def as_markup(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=self.export())


class ReplyKeyboardBuilder(_KeyboardBuilder[KeyboardButton]):
    """Builder for the reply keyboard shown instead of the system keyboard."""

    def button(
        self,
        text: str,
        *,
        request_contact: bool | None = None,
        request_location: bool | None = None,
        web_app: WebAppInfo | str | None = None,
    ) -> ReplyKeyboardBuilder:
        if isinstance(web_app, str):
            web_app = WebAppInfo(url=web_app)
        return self.add(  # type: ignore[no-any-return]
            KeyboardButton(
                text=text,
                request_contact=request_contact,
                request_location=request_location,
                web_app=web_app,
            )
        )

    def as_markup(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(keyboard=self.export())
