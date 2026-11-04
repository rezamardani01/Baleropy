from __future__ import annotations

from typing import Any

from baleropy import Bot
from baleropy.dispatcher import UNHANDLED, Dispatcher
from baleropy.filters import Command, StateFilter
from baleropy.fsm import (
    FSMContext,
    FSMContextMiddleware,
    FSMStrategy,
    MemoryStorage,
    State,
    StatesGroup,
    StorageKey,
    any_state,
    default_state,
)
from baleropy.types import Update


class Form(StatesGroup):
    name = State()
    age = State()

    class Extra(StatesGroup):
        city = State()


def update(text: str, user: int = 1, chat: int = 1, update_id: int = 1) -> Update:
    return Update.model_validate(
        {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "date": 1,
                "from": {"id": user, "first_name": "U"},
                "chat": {"id": chat, "type": "private"},
                "text": text,
            },
        }
    )


def test_state_names() -> None:
    assert Form.name.state == "Form:name"
    assert Form.Extra.city.state == "Form.Extra:city"
    assert Form.__all_states_names__ == ("Form:name", "Form:age", "Form.Extra:city")
    assert "Form:age" in Form
    assert Form.age in Form
    assert Form.name == "Form:name"
    assert default_state.state is None
    assert any_state.state == "*"


async def test_memory_storage_roundtrip() -> None:
    storage = MemoryStorage()
    key = StorageKey(1, 2, 3)
    assert await storage.get_state(key) is None
    assert await storage.get_data(key) == {}
    await storage.set_state(key, Form.name)
    await storage.update_data(key, {"a": 1})
    await storage.update_data(key, {"b": [1]})
    assert await storage.get_state(key) == "Form:name"
    data = await storage.get_data(key)
    assert data == {"a": 1, "b": [1]}
    data["b"].append(2)  # mutating the copy must not leak into the storage
    assert (await storage.get_data(key))["b"] == [1]
    other = StorageKey(1, 2, 4)
    assert await storage.get_state(other) is None


async def test_context_helpers() -> None:
    ctx = FSMContext(MemoryStorage(), StorageKey(1, 1, 1))
    await ctx.set_state(Form.age)
    await ctx.update_data(x=1)
    await ctx.update_data({"y": 2})
    assert await ctx.get_value("y") == 2
    assert await ctx.get_value("missing", "d") == "d"
    await ctx.clear()
    assert await ctx.get_state() is None
    assert await ctx.get_data() == {}


async def test_conversation_flow() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()

    @dp.message(Command("form"))
    async def start(state: FSMContext) -> str:
        await state.set_state(Form.name)
        return "ask-name"

    @dp.message(Form.name)
    async def got_name(message: Any, state: FSMContext) -> str:
        await state.update_data(name=message.text)
        await state.set_state(Form.age)
        return "ask-age"

    @dp.message(StateFilter(Form.age))
    async def got_age(message: Any, state: FSMContext) -> dict[str, Any]:
        await state.update_data(age=message.text)
        data = await state.get_data()
        await state.clear()
        return data

    @dp.message(default_state)
    async def idle() -> str:
        return "idle"

    assert await dp.feed_update(bot, update("hello")) == "idle"
    assert await dp.feed_update(bot, update("/form")) == "ask-name"
    assert await dp.feed_update(bot, update("Reza")) == "ask-age"
    assert await dp.feed_update(bot, update("30")) == {"name": "Reza", "age": "30"}
    assert await dp.feed_update(bot, update("again")) == "idle"


async def test_state_is_isolated_per_user() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()

    @dp.message(Command("go"))
    async def go(state: FSMContext) -> None:
        await state.set_state(Form.name)

    @dp.message(Form.name)
    async def in_form() -> str:
        return "in-form"

    await dp.feed_update(bot, update("/go", user=1))
    assert await dp.feed_update(bot, update("x", user=1)) == "in-form"
    assert await dp.feed_update(bot, update("x", user=2)) is UNHANDLED


async def test_state_filter_group_and_wildcard() -> None:
    flt = StateFilter(Form)
    assert await flt(None, raw_state="Form:age")
    assert await flt(None, raw_state="Form.Extra:city")
    assert not await flt(None, raw_state="Other:x")
    assert not await flt(None, raw_state=None)
    assert await StateFilter(None)(None, raw_state=None)
    assert await StateFilter("*")(None, raw_state="whatever")
    assert await StateFilter(any_state)(None, raw_state="whatever")


def test_strategies() -> None:
    storage = MemoryStorage()
    user_in_chat = FSMContextMiddleware(storage, FSMStrategy.USER_IN_CHAT)
    chat = FSMContextMiddleware(storage, FSMStrategy.CHAT)
    global_user = FSMContextMiddleware(storage, FSMStrategy.GLOBAL_USER)
    assert user_in_chat.resolve_key(9, 10, 11) == StorageKey(9, 10, 11)
    assert chat.resolve_key(9, 10, 11) == StorageKey(9, 10, 10)
    assert global_user.resolve_key(9, 10, 11) == StorageKey(9, 11, 11)
    assert user_in_chat.resolve_key(9, None, None) is None
