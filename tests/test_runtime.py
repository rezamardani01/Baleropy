from __future__ import annotations

import asyncio
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from baleropy import Bot
from baleropy.client.server import ApiServer
from baleropy.client.session.aiohttp import AiohttpSession
from baleropy.dispatcher import UNHANDLED, Dispatcher
from baleropy.dispatcher.middlewares import (
    CallbackAnswerMiddleware,
    LoggingMiddleware,
    ThrottlingMiddleware,
)
from baleropy.types import Update
from baleropy.webhook import SimpleRequestHandler, secret_path


def message_update(text: str, update_id: int = 1, user: int = 1) -> dict[str, Any]:
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id,
            "date": 1,
            "from": {"id": user, "first_name": "U"},
            "chat": {"id": user, "type": "private"},
            "text": text,
        },
    }


# --- middlewares -----------------------------------------------------------------------------
async def test_throttling_drops_and_warns_once() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()
    warned: list[int] = []

    async def on_throttled(event: Any, data: dict[str, Any]) -> None:
        warned.append(data["event_from_user"].id)

    dp.message.outer_middleware(ThrottlingMiddleware(rate=0.2, on_throttled=on_throttled))
    hits: list[str] = []

    @dp.message()
    async def handler(message: Any) -> None:
        hits.append(message.text)

    for i, text in enumerate(["a", "b", "c"], start=1):
        await dp.feed_update(bot, Update.model_validate(message_update(text, i)))
    await asyncio.sleep(0.25)
    await dp.feed_update(bot, Update.model_validate(message_update("d", 4)))
    await dp.feed_update(bot, Update.model_validate(message_update("other-user", 5, user=2)))
    assert hits == ["a", "d", "other-user"]
    assert warned == [1]


async def test_logging_middleware_reraises(caplog: pytest.LogCaptureFixture) -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()
    dp.message.outer_middleware(LoggingMiddleware())

    @dp.message()
    async def boom() -> None:
        raise RuntimeError("x")

    with caplog.at_level("INFO", logger="baleropy.middleware"), pytest.raises(RuntimeError):
        await dp.feed_update(bot, Update.model_validate(message_update("a")))
    assert any("failed" in r.message for r in caplog.records)


async def test_callback_answer_middleware() -> None:
    answers: list[str] = []

    class FakeBot(Bot):
        async def answer_callback_query(  # type: ignore[override]
            self, callback_query_id: str, text: str | None = None, show_alert: bool | None = None
        ) -> bool:
            answers.append(f"{callback_query_id}:{text}")
            return True

    bot = FakeBot("1:abc")
    dp = Dispatcher()
    dp.callback_query.outer_middleware(CallbackAnswerMiddleware(text="auto"))

    @dp.callback_query(lambda q: q.data == "manual")
    async def manual(query: Any) -> None:
        await query.answer("mine")

    @dp.callback_query()
    async def lazy() -> None: ...

    def update(data: str, qid: str) -> Update:
        return Update.model_validate(
            {
                "update_id": 1,
                "callback_query": {"id": qid, "from": {"id": 1, "first_name": "A"}, "data": data},
            },
            context={"bot": bot},
        )

    await dp.feed_update(bot, update("manual", "9"))
    await dp.feed_update(bot, update("other", "8"))
    await dp.feed_update(bot, update("other", "1-old"))  # old clients are never answered
    assert answers == ["9:mine", "8:auto"]


# --- webhook ---------------------------------------------------------------------------------
async def test_webhook_handler() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()
    seen: list[str] = []

    @dp.message()
    async def handler(message: Any) -> None:
        seen.append(message.text)

    path = secret_path()
    app = web.Application()
    SimpleRequestHandler(dp, bot, handle_in_background=False).register(app, path)
    async with TestClient(TestServer(app)) as client:
        ok = await client.post(path, json=message_update("via-webhook"))
        assert ok.status == 200
        bad = await client.post(path, data=b"not json")
        assert bad.status == 400
        wrong = await client.post("/webhook/guess", json=message_update("x"))
        assert wrong.status == 404
    assert seen == ["via-webhook"]
    assert secret_path() != secret_path()


async def test_webhook_verify_rejects() -> None:
    bot = Bot("1:abc")
    app = web.Application()
    SimpleRequestHandler(Dispatcher(), bot, verify=lambda request: False).register(app, "/w")
    async with TestClient(TestServer(app)) as client:
        assert (await client.post("/w", json=message_update("x"))).status == 403


# --- polling against a fake Bale server ------------------------------------------------------
async def test_polling_end_to_end() -> None:
    sent: list[dict[str, Any]] = []
    queue = [[message_update("/ping", 10)], [message_update("second", 11)], [], [], [], []]
    offsets: list[Any] = []
    stop_holder: dict[str, Dispatcher] = {}

    async def api(request: web.Request) -> web.Response:
        method = request.match_info["method"]
        body = await request.json() if request.can_read_body else {}
        if method == "deleteWebhook":
            return web.json_response({"ok": True, "result": True})
        if method == "getUpdates":
            offsets.append(body.get("offset"))
            await asyncio.sleep(0.01)
            batch = queue.pop(0) if queue else []
            return web.json_response({"ok": True, "result": batch})
        if method == "sendMessage":
            sent.append(body)
            return web.json_response(
                {
                    "ok": True,
                    "result": {
                        "message_id": 1,
                        "date": 1,
                        "chat": {"id": body["chat_id"], "type": "private"},
                    },
                }
            )
        return web.json_response({"ok": False, "error_code": 404}, status=404)

    app = web.Application()
    app.router.add_route("*", "/bot{token}/{method}", api)
    server = TestServer(app)
    await server.start_server()
    bot = Bot(
        "1:abc",
        session=AiohttpSession(),
        server=ApiServer.from_base(str(server.make_url("")).rstrip("/")),
    )
    dp = Dispatcher()
    stop_holder["dp"] = dp
    lifecycle: list[str] = []

    @dp.on_startup
    async def started() -> None:
        lifecycle.append("up")

    @dp.on_shutdown
    async def stopped() -> None:
        lifecycle.append("down")

    @dp.message()
    async def echo(message: Any) -> None:
        await message.answer(f"echo:{message.text}")
        if message.text == "second":
            await dp.stop_polling()

    try:
        await asyncio.wait_for(dp.start_polling(bot, polling_timeout=0), timeout=10)
    finally:
        await server.close()

    assert [m["text"] for m in sent] == ["echo:/ping", "echo:second"]
    assert offsets[:2] == [None, 11]  # offset acknowledges processed updates
    assert lifecycle == ["up", "down"]


async def test_polling_requires_bot() -> None:
    with pytest.raises(ValueError):
        await Dispatcher().start_polling()


async def test_polling_cancellation_waits_for_polling_tasks() -> None:
    started = asyncio.Event()
    cleaned_up = asyncio.Event()
    session_closed = asyncio.Event()

    class BlockingBot(Bot):
        async def delete_webhook(self) -> bool:
            return True

        async def get_updates(
            self,
            offset: int | None = None,
            limit: int | None = None,
            timeout: int | None = None,
        ) -> list[Update]:
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned_up.set()
            return []

        async def close(self) -> None:
            session_closed.set()

    bot = BlockingBot("1:abc")
    task = asyncio.create_task(Dispatcher().start_polling(bot, polling_timeout=30))
    await asyncio.wait_for(started.wait(), timeout=1)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    assert cleaned_up.is_set()
    assert session_closed.is_set()


def test_run_polling_suppresses_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupt(coroutine: Any) -> None:
        coroutine.close()
        raise KeyboardInterrupt

    monkeypatch.setattr(asyncio, "run", interrupt)
    Dispatcher().run_polling(Bot("1:abc"))


def test_feed_unknown_update_is_unhandled() -> None:
    dp = Dispatcher()
    bot = Bot("1:abc")
    result = asyncio.run(dp.feed_update(bot, Update(update_id=1)))
    assert result is UNHANDLED


async def test_unknown_update_reaches_catch_all_handler() -> None:
    bot = Bot("1:abc")
    dp = Dispatcher()
    unknown: list[dict[str, Any]] = []

    @dp.unknown()
    async def handle(update: Update) -> None:
        unknown.append(update.unknown_event_types)

    update = Update.model_validate({"update_id": 1, "future_event": {"value": 42}})
    await dp.feed_update(bot, update)

    assert unknown == [{"future_event": {"value": 42}}]
