"""Live smoke test against the real Bale API.

    BALE_TOKEN=123:abc python scripts/smoke_test.py            # read-only checks
    BALE_TOKEN=123:abc BALE_CHAT_ID=999 python scripts/smoke_test.py   # also sends messages

The token is only read from the environment and never printed or stored.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

from baleropy import Bot
from baleropy.exceptions import BaleropyError
from baleropy.types import BufferedInputFile
from baleropy.utils import InlineKeyboardBuilder

results: list[tuple[str, bool, str]] = []


async def check(name: str, coro) -> object | None:  # type: ignore[no-untyped-def]
    started = time.perf_counter()
    try:
        value = await coro
    except BaleropyError as error:
        results.append((name, False, f"{type(error).__name__}: {error}"))
        return None
    except Exception as error:  # a decode/validation bug in baleropy itself
        results.append((name, False, f"BUG {type(error).__name__}: {error}"))
        return None
    results.append((name, True, f"{(time.perf_counter() - started) * 1000:.0f} ms"))
    return value


async def main() -> int:
    token = os.environ.get("BALE_TOKEN")
    if not token:
        print("Set BALE_TOKEN first.")
        return 2
    chat_id = os.environ.get("BALE_CHAT_ID")
    chat: int | str | None = int(chat_id) if chat_id and chat_id.lstrip("-").isdigit() else chat_id

    async with Bot(token) as bot:
        me = await check("getMe", bot.get_me())
        await check("getWebhookInfo", bot.get_webhook_info())
        await check("deleteWebhook", bot.delete_webhook())
        updates = await check("getUpdates(timeout=0)", bot.get_updates(limit=5, timeout=0))
        if updates:
            print("  sample update keys:", sorted(updates[0].model_dump(exclude_none=True)))  # type: ignore[index]

        if chat is not None:
            sent = await check("sendMessage", bot.send_message(chat, "baleropy smoke test"))
            kb = InlineKeyboardBuilder().button(text="ok", callback_data="smoke:ok").as_markup()
            await check("sendMessage+inline", bot.send_message(chat, "keyboard", reply_markup=kb))
            await check("sendChatAction", bot.send_chat_action(chat, "typing"))
            await check(
                "sendDocument(upload)",
                bot.send_document(chat, BufferedInputFile(b"hello baleropy", "hello.txt")),
            )
            await check("getChat", bot.get_chat(chat))
            if sent is not None:
                mid = sent.message_id  # type: ignore[attr-defined]
                await check("editMessageText", bot.edit_message_text(chat, mid, "edited"))
                await check("deleteMessage", bot.delete_message(chat, mid))

    print(f"\nBot: {getattr(me, 'username', None)!r}")
    width = max(len(n) for n, _, _ in results)
    for name, ok, info in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {info}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
