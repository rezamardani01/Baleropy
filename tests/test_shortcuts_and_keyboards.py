from __future__ import annotations

from typing import Any

import pytest

from balegram.filters import CallbackData
from balegram.types import CallbackQuery, Message
from balegram.utils import InlineKeyboardBuilder, ReplyKeyboardBuilder


class RecordingBot:
    """Stands in for Bot: records calls made through the shortcuts."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:
        async def call(*args: Any, **kwargs: Any) -> str:
            self.calls.append((name, args, kwargs))
            return "ok"

        return call


def make_message(bot: RecordingBot, **extra: Any) -> Message:
    return Message.model_validate(
        {
            "message_id": 5,
            "date": 1,
            "from": {"id": 7, "first_name": "A"},
            "chat": {"id": 42, "type": "private"},
            "text": "hi",
            **extra,
        },
        context={"bot": bot},
    )


async def test_answer_and_reply() -> None:
    bot = RecordingBot()
    msg = make_message(bot)
    await msg.answer("a")
    await msg.reply("r")
    assert bot.calls[0] == (
        "send_message",
        (42, "a"),
        {"reply_to_message_id": None, "reply_markup": None},
    )
    assert bot.calls[1][2]["reply_to_message_id"] == 5


async def test_edit_delete_forward_copy() -> None:
    bot = RecordingBot()
    msg = make_message(bot)
    await msg.edit_text("new")
    await msg.delete()
    await msg.forward(9)
    await msg.copy_to(9)
    assert [c[0] for c in bot.calls] == [
        "edit_message_text",
        "delete_message",
        "forward_message",
        "copy_message",
    ]
    assert bot.calls[0][1][:3] == (42, 5, "new")
    assert bot.calls[2][1] == (9, 42, 5)


async def test_download_uses_largest_photo() -> None:
    bot = RecordingBot()
    msg = make_message(
        bot,
        text=None,
        photo=[
            {"file_id": "small", "file_unique_id": "s", "width": 1, "height": 1},
            {"file_id": "big", "file_unique_id": "b", "width": 9, "height": 9},
        ],
    )
    assert msg.file_id == "big"
    await msg.download()
    assert bot.calls[0] == ("download", ("big", None), {})
    with pytest.raises(ValueError):
        await make_message(bot).download()


async def test_unbound_object_raises() -> None:
    msg = Message.model_validate(
        {"message_id": 1, "date": 1, "chat": {"id": 1, "type": "private"}, "text": "x"}
    )
    with pytest.raises(RuntimeError, match="not bound"):
        await msg.answer("x")


async def test_callback_answer_skips_old_clients() -> None:
    bot = RecordingBot()

    def query(query_id: str) -> CallbackQuery:
        return CallbackQuery.model_validate(
            {"id": query_id, "from": {"id": 1, "first_name": "A"}, "data": "x"},
            context={"bot": bot},
        )

    assert await query("1234").answer("hey") is False
    assert bot.calls == []
    await query("9234").answer("hey", show_alert=True)
    assert bot.calls == [("answer_callback_query", ("9234", "hey", True), {})]


def test_inline_builder_layout() -> None:
    class Page(CallbackData, prefix="p"):
        n: int

    builder = InlineKeyboardBuilder()
    for n in range(5):
        builder.button(text=str(n), callback_data=Page(n=n))
    builder.adjust(2, 1)
    markup = builder.as_markup()
    assert [len(r) for r in markup.inline_keyboard] == [2, 1, 1, 1]
    assert markup.inline_keyboard[0][1].callback_data == "p:1"

    builder.adjust(2, 1, repeat=True)
    assert [len(r) for r in builder.as_markup().inline_keyboard] == [2, 1, 2]


def test_inline_builder_rules() -> None:
    builder = InlineKeyboardBuilder()
    with pytest.raises(ValueError):
        builder.button(text="x", callback_data="a", url="https://x.y")
    builder.button(text="app", web_app="https://x.y").button(text="copy", copy_text="abc")
    keyboard = builder.as_markup().inline_keyboard[0]
    assert keyboard[0].web_app is not None and keyboard[1].copy_text is not None
    builder.row(*builder.export()[0], width=1)
    assert [len(r) for r in builder.export()] == [2, 1, 1]
    with pytest.raises(ValueError):
        InlineKeyboardBuilder().row(*[builder.export()[0][0]] * 101)


def test_reply_builder_serialization() -> None:
    markup = (
        ReplyKeyboardBuilder()
        .button(text="Share", request_contact=True)
        .button(text="Plain")
        .as_markup()
    )
    dumped = markup.model_dump(exclude_none=True)
    assert dumped == {"keyboard": [[{"text": "Share", "request_contact": True}, {"text": "Plain"}]]}
