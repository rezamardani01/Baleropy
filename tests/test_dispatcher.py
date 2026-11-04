from __future__ import annotations

from typing import Any

import pytest

from baleropy import Bot
from baleropy.dispatcher import UNHANDLED, BaseMiddleware, Dispatcher, ErrorEvent, Router
from baleropy.exceptions import CancelHandler, SkipHandler
from baleropy.filters import Filter
from baleropy.types import Update


def make_update(text: str = "hi", user_id: int = 1, update_id: int = 1) -> Update:
    return Update.model_validate(
        {
            "update_id": update_id,
            "message": {
                "message_id": 10,
                "date": 1,
                "from": {"id": user_id, "first_name": "A"},
                "chat": {"id": user_id, "type": "private"},
                "text": text,
            },
        }
    )


@pytest.fixture
def bot() -> Bot:
    return Bot("1:abc")


async def test_handler_receives_event_and_injected_data(bot: Bot) -> None:
    dp = Dispatcher(answer=42)
    seen: dict[str, Any] = {}

    @dp.message()
    async def handler(message: Any, bot: Bot, answer: int, event_from_user: Any) -> str:
        seen.update(text=message.text, bot=bot, answer=answer, user=event_from_user.id)
        return "done"

    assert await dp.feed_update(bot, make_update("yo")) == "done"
    assert seen == {"text": "yo", "bot": bot, "answer": 42, "user": 1}


async def test_unhandled_event(bot: Bot) -> None:
    dp = Dispatcher()
    assert await dp.feed_update(bot, make_update()) is UNHANDLED


async def test_filters_and_first_match_wins(bot: Bot) -> None:
    dp = Dispatcher()
    calls: list[str] = []

    @dp.message(lambda m: m.text == "a")
    async def first(message: Any) -> None:
        calls.append("first")

    @dp.message()
    async def fallback(message: Any) -> None:
        calls.append("fallback")

    await dp.feed_update(bot, make_update("a"))
    await dp.feed_update(bot, make_update("b"))
    assert calls == ["first", "fallback"]


async def test_filter_can_inject_data(bot: Bot) -> None:
    class Words(Filter):
        async def __call__(self, event: Any, **data: Any) -> bool | dict[str, Any]:
            words = event.text.split()
            return {"words": words} if len(words) > 1 else False

    dp = Dispatcher()

    @dp.message(Words())
    async def handler(words: list[str]) -> list[str]:
        return words

    assert await dp.feed_update(bot, make_update("a b")) == ["a", "b"]
    assert await dp.feed_update(bot, make_update("single")) is UNHANDLED


async def test_filter_operators(bot: Bot) -> None:
    class Starts(Filter):
        def __init__(self, prefix: str) -> None:
            self.prefix = prefix

        async def __call__(self, event: Any, **data: Any) -> bool:
            return bool(event.text.startswith(self.prefix))

    dp = Dispatcher()

    @dp.message(Starts("a") | Starts("b"), ~Starts("bad"))
    async def handler() -> str:
        return "ok"

    assert await dp.feed_update(bot, make_update("apple")) == "ok"
    assert await dp.feed_update(bot, make_update("banana")) == "ok"
    assert await dp.feed_update(bot, make_update("bad")) is UNHANDLED
    assert await dp.feed_update(bot, make_update("cat")) is UNHANDLED


async def test_sync_handler_runs(bot: Bot) -> None:
    dp = Dispatcher()

    @dp.message()
    def handler(message: Any) -> str:
        return message.text.upper()

    assert await dp.feed_update(bot, make_update("x")) == "X"


async def test_nested_routers_order_and_loop_protection(bot: Bot) -> None:
    dp, child, grand = Dispatcher(), Router(name="child"), Router(name="grand")
    dp.include_router(child)
    child.include_router(grand)
    order: list[str] = []

    @grand.message()
    async def deep() -> None:
        order.append("grand")

    @dp.message(lambda m: m.text == "root")
    async def root() -> None:
        order.append("root")

    await dp.feed_update(bot, make_update("x"))
    await dp.feed_update(bot, make_update("root"))
    assert order == ["grand", "root"]
    with pytest.raises(RuntimeError):
        grand.include_router(dp)
    with pytest.raises(RuntimeError):
        dp.include_router(child)  # already attached


async def test_skip_handler(bot: Bot) -> None:
    dp = Dispatcher()

    @dp.message()
    async def first() -> None:
        raise SkipHandler

    @dp.message()
    async def second() -> str:
        return "second"

    assert await dp.feed_update(bot, make_update()) == "second"


async def test_middlewares_order_and_data(bot: Bot) -> None:
    dp = Dispatcher()
    router = Router()
    dp.include_router(router)
    trace: list[str] = []

    @dp.update.outer_middleware
    async def update_mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
        trace.append("update-in")
        result = await handler(event, data)
        trace.append("update-out")
        return result

    @router.message.outer_middleware
    async def outer(handler: Any, event: Any, data: dict[str, Any]) -> Any:
        trace.append("outer")
        return await handler(event, data)

    class Inner(BaseMiddleware):
        async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
            trace.append("inner")
            data["extra"] = "from-mw"
            return await handler(event, data)

    router.message.middleware(Inner())

    @router.message(lambda m: trace.append("filter") or True)
    async def h(extra: str) -> str:
        trace.append("handler")
        return extra

    assert await dp.feed_update(bot, make_update()) == "from-mw"
    assert trace == ["update-in", "outer", "filter", "inner", "handler", "update-out"]


async def test_inner_middleware_skipped_when_no_handler_selected(bot: Bot) -> None:
    dp = Dispatcher()
    hits: list[int] = []

    @dp.message.middleware
    async def mw(handler: Any, event: Any, data: dict[str, Any]) -> Any:
        hits.append(1)
        return await handler(event, data)

    @dp.message(lambda m: False)
    async def never() -> None: ...

    await dp.feed_update(bot, make_update())
    assert hits == []


async def test_middleware_can_cancel(bot: Bot) -> None:
    dp = Dispatcher()

    @dp.message.outer_middleware
    async def blocker(handler: Any, event: Any, data: dict[str, Any]) -> Any:
        raise CancelHandler

    @dp.message()
    async def never() -> str:
        return "no"

    assert await dp.feed_update(bot, make_update()) is UNHANDLED


async def test_error_handler(bot: Bot) -> None:
    dp = Dispatcher()

    @dp.message()
    async def boom() -> None:
        raise ValueError("bad")

    with pytest.raises(ValueError, match="bad"):
        await dp.feed_update(bot, make_update())

    @dp.error()
    async def on_error(event: ErrorEvent, exception: Exception) -> str:
        assert event.exception is exception
        return f"handled {exception}"

    assert await dp.feed_update(bot, make_update()) == "handled bad"


async def test_startup_shutdown_callbacks() -> None:
    dp = Dispatcher(token="t")
    child = Router()
    dp.include_router(child)
    log: list[str] = []

    @dp.on_startup
    async def up(token: str) -> None:
        log.append(f"up:{token}")

    @child.on_shutdown
    def down() -> None:
        log.append("down")

    await dp.emit_startup(token="x")
    await dp.emit_shutdown()
    assert log == ["up:x", "down"]
