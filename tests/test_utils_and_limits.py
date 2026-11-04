from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from baleropy import Bot, F
from baleropy.dispatcher import Dispatcher, ErrorEvent, get_flag
from baleropy.filters import (
    CommandStart,
    ExceptionMessageFilter,
    ExceptionTypeFilter,
    MagicData,
)
from baleropy.methods import (
    AnswerCallbackQuery,
    CreateInvoiceLink,
    CreateNewStickerSet,
    SendMessage,
)
from baleropy.methods.media_group import InputMediaPhoto
from baleropy.methods.misc import InputSticker
from baleropy.types import BufferedInputFile, LabeledPrice, Message, Update
from baleropy.utils import (
    ChatActionSender,
    MediaGroupBuilder,
    bold,
    bot_link,
    create_start_link,
    decode_payload,
    encode_payload,
    italic,
    link,
    split_text,
)


# --- documented limits -----------------------------------------------------------------------
def test_text_limits() -> None:
    SendMessage(chat_id=1, text="x" * 4096)
    with pytest.raises(ValidationError):
        SendMessage(chat_id=1, text="x" * 4097)
    with pytest.raises(ValidationError):
        SendMessage(chat_id=1, text="")


def test_other_limits() -> None:
    AnswerCallbackQuery(callback_query_id="1", text="x" * 200)
    with pytest.raises(ValidationError):
        AnswerCallbackQuery(callback_query_id="1", text="x" * 201)
    with pytest.raises(ValidationError):
        InputMediaPhoto(media="id", caption="x" * 1025)
    prices = [LabeledPrice(label="a", amount=1)]
    base: dict[str, Any] = {"description": "d", "provider_token": "t", "prices": prices}
    CreateInvoiceLink(title="t" * 32, payload="p" * 128, **base)
    with pytest.raises(ValidationError):
        CreateInvoiceLink(title="t" * 33, payload="p", **base)
    with pytest.raises(ValidationError):
        CreateInvoiceLink(title="t", payload="é" * 65, **base)  # 130 bytes
    sticker = InputSticker(sticker="id")
    with pytest.raises(ValidationError):
        CreateNewStickerSet(user_id=1, name="n", title="t", stickers=[])
    with pytest.raises(ValidationError):
        CreateNewStickerSet(user_id=1, name="n" * 65, title="t", stickers=[sticker])


# --- text helpers ----------------------------------------------------------------------------
def test_markdown_helpers() -> None:
    assert f"a {bold('b')} c {italic('d')} {link('x', 'https://y.z')}" == (
        "a **b** c __d__ [x](https://y.z)"
    )


def test_split_text() -> None:
    assert split_text("short") == ["short"]
    text = "\n".join(["line"] * 1000)
    chunks = split_text(text, 100)
    assert all(len(c) <= 100 for c in chunks)
    assert "\n".join(chunks).replace("\n", "") == text.replace("\n", "")
    words = split_text("word " * 50, 21)
    assert all(len(c) <= 21 for c in words) and all(c.endswith("word") for c in words)
    assert split_text("x" * 25, 10) == ["x" * 10, "x" * 10, "x" * 5]
    with pytest.raises(ValueError):
        split_text("x", 0)


# --- deep links ------------------------------------------------------------------------------
async def test_deep_links() -> None:
    assert bot_link("@MyBot") == "https://ble.ir/MyBot"
    assert bot_link("MyBot", "ref 1") == "https://ble.ir/MyBot?start=ref%201"
    encoded = bot_link("MyBot", "id=5&x", encode=True)
    payload = encoded.split("start=")[1]
    assert decode_payload(payload) == "id=5&x"
    assert decode_payload(encode_payload("سلام")) == "سلام"

    class FakeBot:
        async def me(self) -> Any:
            return type("U", (), {"username": "shop_bot"})()

    assert await create_start_link(FakeBot(), "p1") == "https://ble.ir/shop_bot?start=p1"  # type: ignore[arg-type]

    # round trip through the CommandStart filter
    message = Message.model_validate(
        {
            "message_id": 1,
            "date": 1,
            "chat": {"id": 1, "type": "private"},
            "text": f"/start {payload}",
        }
    )
    result = await CommandStart(deep_link=True, encoded=True)(message)
    assert isinstance(result, dict) and result["command"].args == "id=5&x"


# --- chat action sender ----------------------------------------------------------------------
async def test_chat_action_sender_repeats_and_stops() -> None:
    sent: list[tuple[Any, Any]] = []

    class FakeBot:
        async def send_chat_action(self, chat_id: Any, action: Any) -> None:
            sent.append((chat_id, getattr(action, "value", action)))

    async with ChatActionSender.typing(FakeBot(), 7, interval=0.05):  # type: ignore[arg-type]
        await asyncio.sleep(0.18)
    count = len(sent)
    assert count >= 3 and set(sent) == {(7, "typing")}
    await asyncio.sleep(0.15)
    assert len(sent) == count  # stopped when the block ended


# --- media group builder ---------------------------------------------------------------------
def test_media_group_builder() -> None:
    album = MediaGroupBuilder(caption="trip")
    album.add_photo(BufferedInputFile(b"1", "1.png")).add_photo("file_id", caption="own")
    items = album.build()
    assert [i.type for i in items] == ["photo", "photo"]
    assert items[0].caption == "trip" and items[1].caption == "own"
    with pytest.raises(ValueError):
        MediaGroupBuilder().add_photo("a").build()
    big = MediaGroupBuilder()
    for _ in range(10):
        big.add_document("d")
    with pytest.raises(ValueError):
        big.add_document("d")


# --- extra filters and flags -----------------------------------------------------------------
def make_update(text: str = "hi") -> Update:
    return Update.model_validate(
        {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "date": 1,
                "from": {"id": 7, "first_name": "A"},
                "chat": {"id": 7, "type": "private"},
                "text": text,
            },
        }
    )


async def test_magic_data_and_flags() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher(config=type("Cfg", (), {"owner_id": 7})())
    seen: list[Any] = []

    @dp.message.middleware
    async def spy(handler: Any, event: Any, data: dict[str, Any]) -> Any:
        seen.append(get_flag(data, "rate_limit", default="none"))
        return await handler(event, data)

    @dp.message(MagicData(F.event_from_user.id == F.config.owner_id), rate_limit=5)
    async def owner() -> str:
        return "owner"

    @dp.message()
    async def other() -> str:
        return "other"

    assert await dp.feed_update(bot, make_update()) == "owner"
    assert seen == [5]
    stranger = Dispatcher(config=type("Cfg", (), {"owner_id": 99})())
    stranger.message(MagicData(F.event_from_user.id == F.config.owner_id))(owner)
    stranger.message()(other)
    assert await stranger.feed_update(bot, make_update()) == "other"


async def test_exception_filters() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()

    @dp.message()
    async def boom() -> None:
        raise KeyError("missing-thing")

    @dp.error(ExceptionTypeFilter(ValueError))
    async def value_errors() -> str:
        return "value"

    @dp.error(ExceptionMessageFilter(r"missing-(\w+)"))
    async def by_message(match_exception: Any, event: ErrorEvent) -> str:
        return f"msg:{match_exception.group(1)}"

    assert await dp.feed_update(bot, make_update()) == "msg:thing"


def test_business_bot_uses_business_server() -> None:
    bot = Bot.business("1:abc")
    assert "/business/bot" in bot.server.api_url(bot.token, "sendMessage")
