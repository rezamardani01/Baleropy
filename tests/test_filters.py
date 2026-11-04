from __future__ import annotations

import re
from enum import Enum
from typing import Any

import pytest

from baleropy import Bot
from baleropy.dispatcher import UNHANDLED, Dispatcher
from baleropy.filters import (
    CallbackData,
    ChatTypeFilter,
    Command,
    CommandObject,
    CommandStart,
    F,
)
from baleropy.types import CallbackQuery, Message, Update


def msg(text: str | None = "hi", chat_type: str = "private", **extra: Any) -> Message:
    return Message.model_validate(
        {
            "message_id": 1,
            "date": 1,
            "from": {"id": 7, "first_name": "A"},
            "chat": {"id": 7, "type": chat_type},
            "text": text,
            **extra,
        }
    )


def query(data: str) -> CallbackQuery:
    return CallbackQuery.model_validate(
        {"id": "1", "from": {"id": 7, "first_name": "A"}, "data": data}
    )


async def test_magic_basic_comparisons() -> None:
    assert await (F.text == "hi")(msg("hi")) is True
    assert not await (F.text == "hi")(msg("no"))
    assert await (F.from_user.id.in_({7, 8}))(msg()) is True
    assert not await (F.photo)(msg())  # attribute exists but is None
    assert await (F.text.startswith("h"))(msg("hello")) is True
    assert await (F.text.startswith("H", ignore_case=True))(msg("hello")) is True
    assert await (F.text.len() > 3)(msg("hello")) is True
    assert not await (F.nonexistent.deep.chain == 1)(msg())


async def test_magic_regexp_injects_match() -> None:
    result = await F.text.regexp(r"(\d+)")(msg("order 42"))
    assert isinstance(result, dict)
    assert result["magic_result"].group(1) == "42"


async def test_magic_combinators() -> None:
    flt = (F.text == "a") | (F.text == "b")
    assert await flt(msg("b")) is True
    assert not await flt(msg("c"))
    assert await (~(F.text == "a"))(msg("z")) is True
    both = (F.chat.type == "private") & F.text.contains("x")
    assert await both(msg("axb")) is True
    assert not await both(msg("axb", chat_type="group"))


def test_magic_is_not_bool() -> None:
    with pytest.raises(TypeError):
        bool(F.text == "x")


async def test_magic_with_dispatcher() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()

    @dp.message(F.text.regexp(r"^id:(\d+)$"))
    async def handler(magic_result: re.Match[str]) -> str:
        return magic_result.group(1)

    update = Update(update_id=1, message=msg("id:99"))
    assert await dp.feed_update(bot, update) == "99"
    assert await dp.feed_update(bot, Update(update_id=2, message=msg("nope"))) is UNHANDLED


async def test_command_parsing() -> None:
    result = await Command("start")(msg("/start a b"))
    assert isinstance(result, dict)
    cmd: CommandObject = result["command"]
    assert (cmd.command, cmd.args, cmd.args_list) == ("start", "a b", ["a", "b"])
    assert not await Command("start")(msg("/stop"))
    assert not await Command("start")(msg("start"))
    assert not await Command("start")(msg("/START"))
    assert await Command("start", ignore_case=True)(msg("/START"))
    assert await Command("go", prefix="!")(msg("!go"))
    assert await Command(re.compile(r"item\d+"))(msg("/item12"))
    assert not await Command("start")(msg(None))


async def test_command_mention_checks_bot_username() -> None:
    class FakeBot:
        async def me(self) -> Any:
            return type("U", (), {"username": "MyBot"})()

    assert await Command("start")(msg("/start@mybot"), bot=FakeBot())
    assert not await Command("start")(msg("/start@other"), bot=FakeBot())
    assert await Command("start", ignore_mention=True)(msg("/start@other"), bot=FakeBot())


async def test_command_magic_and_deeplink() -> None:
    assert await Command("x", magic=F.args)(msg("/x 1"))
    assert not await Command("x", magic=F.args)(msg("/x"))
    assert not await CommandStart(deep_link=True)(msg("/start"))
    result = await CommandStart(deep_link=True)(msg("/start ref42"))
    assert isinstance(result, dict) and result["command"].args == "ref42"
    # urlsafe base64 of "hello"
    encoded = await CommandStart(encoded=True)(msg("/start aGVsbG8"))
    assert isinstance(encoded, dict) and encoded["command"].args == "hello"


async def test_chat_type_filter() -> None:
    assert await ChatTypeFilter("private")(msg())
    assert not await ChatTypeFilter("private")(msg(chat_type="group"))
    assert await ChatTypeFilter("group", "channel")(msg(chat_type="channel"))


class Color(str, Enum):
    RED = "red"
    BLUE = "blue"


class Item(CallbackData, prefix="item"):
    id: int
    color: Color
    gift: bool = False
    note: str | None = None


def test_callback_data_roundtrip() -> None:
    original = Item(id=5, color=Color.RED, gift=True)
    packed = original.pack()
    assert packed == "item:5:red:1:"
    assert Item.unpack(packed) == original
    with pytest.raises(ValueError):
        Item(id=1, color=Color.RED, note="bad:value").pack()
    with pytest.raises(ValueError):
        Item.unpack("other:1:red:0:")


def test_callback_data_size_limit() -> None:
    class Big(CallbackData, prefix="big"):
        text: str

    with pytest.raises(ValueError, match="64"):
        Big(text="x" * 100).pack()


async def test_callback_data_filter() -> None:
    flt = Item.filter(F.color == Color.RED)
    result = await flt(query("item:5:red:0:"))
    assert isinstance(result, dict) and result["callback_data"].id == 5
    assert not await flt(query("item:5:blue:0:"))
    assert not await flt(query("other:5:red:0:"))
    assert not await flt(query("item:not-int:red:0:"))


async def test_magic_compares_two_expressions() -> None:
    reply = {"message_id": 4, "date": 1, "chat": {"id": 7, "type": "private"}}
    event = msg("5", reply_to_message=reply)
    assert await (F.chat.id == F.from_user.id)(event) is True  # both are 7
    assert not await (F.message_id > F.reply_to_message.message_id)(event)  # 1 > 4
    assert await (F.message_id < F.reply_to_message.message_id)(event) is True  # 1 < 4
