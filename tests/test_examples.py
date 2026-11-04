"""The shipped examples must keep working: load them and push updates through the dispatcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from balegram import Bot
from balegram.dispatcher import UNHANDLED
from balegram.types import Update

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"example_{name}", EXAMPLES / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeBot(Bot):
    def __init__(self) -> None:
        super().__init__("1:abc")
        self.sent: list[tuple[Any, ...]] = []
        self.answers: list[tuple[Any, ...]] = []

    async def send_message(self, chat_id: Any, text: str, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        self.sent.append((chat_id, text))
        return None

    async def answer_callback_query(self, *args: Any, **kwargs: Any) -> bool:  # type: ignore[override]
        self.answers.append(args)
        return True


def message(text: str, update_id: int = 1, user: int = 5) -> Update:
    return Update.model_validate(
        {
            "update_id": update_id,
            "message": {
                "message_id": update_id,
                "date": 1,
                "from": {"id": user, "first_name": "Reza"},
                "chat": {"id": user, "type": "private"},
                "text": text,
            },
        }
    )


async def test_echo_bot() -> None:
    module = load("echo_bot")
    bot = FakeBot()

    def bound(update: Update) -> Update:
        return Update.model_validate(update.model_dump(by_alias=True), context={"bot": bot})

    await module.dp.feed_update(bot, bound(message("/start")))
    await module.dp.feed_update(bot, bound(message("hello", 2)))
    assert bot.sent == [(5, "سلام Reza!"), (5, "hello")]


async def test_fsm_form_example() -> None:
    module = load("fsm_form")
    bot = FakeBot()

    async def say(text: str, update_id: int) -> None:
        update = message(text, update_id)
        update = Update.model_validate(update.model_dump(by_alias=True), context={"bot": bot})
        await module.dp.feed_update(bot, update)

    for i, text in enumerate(["/form", "Reza", "abc", "30"], start=1):
        await say(text, i)
    assert [t for _, t in bot.sent] == [
        "اسمتان چیست؟",
        "سنتان؟",
        "لطفاً عدد وارد کنید",
        "ثبت شد: Reza (30 ساله)",
    ]


async def test_modular_example(monkeypatch: Any) -> None:
    module = load("modular_bot")
    from balegram import Dispatcher
    from balegram.dispatcher.middlewares import LoggingMiddleware

    bot = FakeBot()
    dp = Dispatcher()
    dp.update.outer_middleware(module.AdminFlagMiddleware())
    dp.message.outer_middleware(LoggingMiddleware())
    dp.include_routers(module.polls, module.admin, module.common)

    def bound(update: Update) -> Update:
        return Update.model_validate(update.model_dump(by_alias=True), context={"bot": bot})

    # /stats is admin-only, user 5 is not an admin
    assert await dp.feed_update(bot, bound(message("/stats", 1))) is UNHANDLED
    module.ADMINS.add(5)
    await dp.feed_update(bot, bound(message("/stats", 2)))
    await dp.feed_update(bot, bound(message("one two three four", 3)))
    assert bot.sent == [(5, "آمار فقط برای ادمین‌ها"), (5, "4 کلمه فرستادید")]


async def test_colored_buttons_example() -> None:
    module = load("colored_buttons")
    bot = FakeBot()
    sent: list[Any] = []

    async def capture(chat_id: Any, text: str, *args: Any, **kwargs: Any) -> None:
        sent.append(kwargs.get("reply_markup") or (args[1] if len(args) > 1 else None))

    bot.send_message = capture  # type: ignore[method-assign]
    update = message("/start")
    update = Update.model_validate(update.model_dump(by_alias=True), context={"bot": bot})
    await module.dp.feed_update(bot, update)
    keyboard = sent[0].inline_keyboard
    styles = [button.style for row in keyboard for button in row]
    assert styles == ["success", "danger", "primary", None]
    assert [len(row) for row in keyboard] == [2, 1, 1]


def test_examples_use_a_token_placeholder() -> None:
    for path in EXAMPLES.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert 'TOKEN = "YOUR_BOT_TOKEN"' in source, path.name
        assert "environ" not in source, path.name
