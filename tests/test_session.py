from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from baleropy import Bot, Button
from baleropy.client.server import ApiServer
from baleropy.client.session.aiohttp import AiohttpSession
from baleropy.exceptions import BaleBadRequest, BaleRetryAfter, BaleUnauthorized, ClientDecodeError
from baleropy.methods import GetMe, SendMediaGroup, SendMessage, SendPhoto
from baleropy.methods.media_group import InputMediaPhoto
from baleropy.types import BufferedInputFile, FSInputFile, User

TOKEN = "123:abc"
Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


@pytest.fixture
async def make_bot() -> AsyncIterator[Callable[[Handler], Awaitable[Bot]]]:
    servers: list[TestServer] = []
    bots: list[Bot] = []

    async def factory(handler: Handler, **session_kwargs: Any) -> Bot:
        app = web.Application()
        app.router.add_route("*", "/bot{token}/{method}", handler)
        app.router.add_route("*", "/file/bot{token}/{path:.*}", handler)
        server = TestServer(app)
        await server.start_server()
        servers.append(server)
        bot = Bot(
            TOKEN,
            session=AiohttpSession(**session_kwargs),
            server=ApiServer.from_base(str(server.make_url("")).rstrip("/")),
        )
        bots.append(bot)
        return bot

    yield factory
    for bot in bots:
        await bot.close()
    for server in servers:
        await server.close()


async def test_get_me_parses_and_binds(make_bot: Any) -> None:
    async def handler(request: web.Request) -> web.Response:
        assert request.match_info["token"] == TOKEN
        assert request.match_info["method"] == "getMe"
        return web.json_response(
            {"ok": True, "result": {"id": 123, "is_bot": True, "first_name": "Bot"}}
        )

    bot = await make_bot(handler)
    me = await bot.get_me()
    assert isinstance(me, User)
    assert me.id == 123
    assert me.bot is bot


async def test_send_message_sends_json_without_nones(make_bot: Any) -> None:
    seen: dict[str, Any] = {}

    async def handler(request: web.Request) -> web.Response:
        seen.update(await request.json())
        return web.json_response(
            {
                "ok": True,
                "result": {"message_id": 7, "date": 1, "chat": {"id": 5, "type": "private"}},
            }
        )

    bot = await make_bot(handler)
    msg = await bot.send_message(5, "hi")
    assert seen == {"chat_id": "5", "text": "hi"}
    assert msg.message_id == 7


async def test_send_message_accepts_nested_button_rows(make_bot: Any) -> None:
    seen: dict[str, Any] = {}

    async def handler(request: web.Request) -> web.Response:
        seen.update(await request.json())
        return web.json_response(
            {
                "ok": True,
                "result": {"message_id": 7, "date": 1, "chat": {"id": 5, "type": "private"}},
            }
        )

    bot = await make_bot(handler)
    await bot.send_message(
        5,
        "Choose:",
        buttons=[
            [Button.inline("One", "1"), Button.inline("Two", "2")],
            [Button.url("Docs", "https://docs.bale.ai")],
        ],
    )
    assert seen["reply_markup"]["inline_keyboard"] == [
        [{"text": "One", "callback_data": "1"}, {"text": "Two", "callback_data": "2"}],
        [{"text": "Docs", "url": "https://docs.bale.ai"}],
    ]


async def test_edit_message_accepts_nested_inline_button_rows(make_bot: Any) -> None:
    seen: list[dict[str, Any]] = []

    async def handler(request: web.Request) -> web.Response:
        seen.append(await request.json())
        return web.json_response({"ok": True, "result": True})

    bot = await make_bot(handler)
    buttons = [[Button.inline("Yes", "yes")], [Button.inline("No", "no")]]
    await bot.edit_message_text(5, 7, "Choose", buttons=buttons)
    await bot.edit_message_caption(5, 7, "Caption", buttons=buttons)
    await bot.edit_message_reply_markup(5, 7, buttons=buttons)
    expected = [
        [{"text": "Yes", "callback_data": "yes"}],
        [{"text": "No", "callback_data": "no"}],
    ]
    assert [request["reply_markup"]["inline_keyboard"] for request in seen] == [
        expected,
        expected,
        expected,
    ]


async def test_errors_are_mapped(make_bot: Any) -> None:
    async def handler(request: web.Request) -> web.Response:
        method = request.match_info["method"]
        if method == "getMe":
            return web.json_response(
                {"ok": False, "error_code": 401, "description": "Unauthorized"}, status=401
            )
        if method == "sendMessage":
            return web.json_response(
                {"ok": False, "error_code": 400, "description": "bad"}, status=400
            )
        return web.json_response(
            {"ok": False, "error_code": 429, "parameters": {"retry_after": 3}}, status=429
        )

    bot = await make_bot(handler, retry_on_flood=0)
    with pytest.raises(BaleUnauthorized):
        await bot.get_me()
    with pytest.raises(BaleBadRequest):
        await bot.send_message(1, "x")
    with pytest.raises(BaleRetryAfter) as info:
        await bot.delete_webhook()
    assert info.value.retry_after == 3


async def test_retry_on_flood(make_bot: Any) -> None:
    calls = 0

    async def handler(request: web.Request) -> web.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return web.json_response(
                {"ok": False, "error_code": 429, "parameters": {"retry_after": 1}}, status=429
            )
        return web.json_response({"ok": True, "result": True})

    bot = await make_bot(handler, retry_on_flood=2)
    assert await bot.delete_webhook() is True
    assert calls == 2


async def test_decode_error(make_bot: Any) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "result": {"unexpected": 1}})

    bot = await make_bot(handler)
    with pytest.raises(ClientDecodeError):
        await bot.get_me()


async def test_multipart_upload(make_bot: Any) -> None:
    seen: dict[str, Any] = {}

    async def handler(request: web.Request) -> web.Response:
        form = await request.post()
        seen["chat_id"] = form["chat_id"]
        upload = form["photo"]
        assert isinstance(upload, web.FileField)
        seen["name"] = upload.filename
        seen["bytes"] = upload.file.read()
        return web.json_response(
            {
                "ok": True,
                "result": {"message_id": 1, "date": 1, "chat": {"id": 1, "type": "private"}},
            }
        )

    bot = await make_bot(handler)
    await bot.send_photo(1, BufferedInputFile(b"PNG", "a.png"), caption="c")
    assert seen == {"chat_id": "1", "name": "a.png", "bytes": b"PNG"}


async def test_filesystem_upload_streams_without_reading_whole_file(
    make_bot: Any, tmp_path: Any, monkeypatch: Any
) -> None:
    content = b"streamed content " * 16384
    path = tmp_path / "large.bin"
    path.write_bytes(content)
    file = FSInputFile(path)
    seen: dict[str, Any] = {}

    async def unexpected_read() -> bytes:
        raise AssertionError("FSInputFile.read should not be used by multipart uploads")

    monkeypatch.setattr(file, "read", unexpected_read)

    async def handler(request: web.Request) -> web.Response:
        form = await request.post()
        upload = form["document"]
        assert isinstance(upload, web.FileField)
        seen["name"] = upload.filename
        seen["bytes"] = upload.file.read()
        return web.json_response(
            {
                "ok": True,
                "result": {"message_id": 1, "date": 1, "chat": {"id": 1, "type": "private"}},
            }
        )

    bot = await make_bot(handler)
    await bot.send_document(1, file)
    assert seen == {"name": "large.bin", "bytes": content}


def test_media_group_attaches_files() -> None:
    method = SendMediaGroup(
        chat_id=1,
        media=[
            InputMediaPhoto(media=BufferedInputFile(b"1", "1.png")),
            InputMediaPhoto(media="existing_file_id", caption="c"),
        ],
    )
    data, files = method.build_request()
    assert list(files) == ["attached0"]
    assert data["media"][0] == {"type": "photo", "media": "attach://attached0"}
    assert data["media"][1]["media"] == "existing_file_id"


async def test_request_middleware(make_bot: Any) -> None:
    async def handler(request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "result": True})

    bot = await make_bot(handler)
    names: list[str] = []

    @bot.session.middleware
    async def spy(nxt: Any, bot: Bot, method: Any) -> Any:
        names.append(method.__api_method__)
        return await nxt(bot, method)

    await bot.delete_webhook()
    assert names == ["deleteWebhook"]


def test_token_validation() -> None:
    with pytest.raises(ValueError):
        Bot("bad-token")


def test_method_names() -> None:
    assert GetMe.__api_method__ == "getMe"
    assert SendMessage(chat_id=1, text="a").__api_method__ == "sendMessage"
    assert SendPhoto(chat_id=1, photo="x").__api_method__ == "sendPhoto"


async def test_flood_pause_is_shared_between_parallel_requests(make_bot: Any) -> None:
    """After one 429 the other in-flight requests must wait instead of hammering the server."""
    import asyncio

    hits: list[float] = []
    loop = asyncio.get_running_loop()
    blocked_until = 0.0

    async def handler(request: web.Request) -> web.Response:
        nonlocal blocked_until
        now = loop.time()
        hits.append(now)
        if len(hits) == 1:
            blocked_until = now + 1
        if now < blocked_until:
            return web.json_response(
                {"ok": False, "error_code": 429, "parameters": {"retry_after": 1}}, status=429
            )
        return web.json_response({"ok": True, "result": True})

    bot = await make_bot(handler)
    results = await asyncio.gather(*(bot.delete_webhook() for _ in range(5)))
    assert results == [True] * 5
    # first wave of 5 requests (one 429 each at most), then exactly one retry per request
    assert len(hits) <= 10


async def test_flood_retries_are_bounded(make_bot: Any) -> None:
    calls = 0

    async def handler(request: web.Request) -> web.Response:
        nonlocal calls
        calls += 1
        return web.json_response(
            {"ok": False, "error_code": 429, "parameters": {"retry_after": 0}}, status=429
        )

    bot = await make_bot(handler, max_flood_retries=2)
    with pytest.raises(BaleRetryAfter):
        await bot.delete_webhook()
    assert calls == 3  # first try + 2 retries


def test_chat_ids_are_sent_as_strings() -> None:
    """Bale answers 'chat id is empty' to an integer chat_id on sendChatAction."""
    from baleropy.methods import ForwardMessage, SendChatAction

    data, _ = SendChatAction(chat_id=1284000539, action="typing").build_request()
    assert data == {"chat_id": "1284000539", "action": "typing"}
    data, _ = SendChatAction(chat_id="@channel", action="typing").build_request()
    assert data["chat_id"] == "@channel"
    data, _ = ForwardMessage(chat_id=-5, from_chat_id=7, message_id=1).build_request()
    assert data == {"chat_id": "-5", "from_chat_id": "7", "message_id": 1}
