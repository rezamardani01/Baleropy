"""Run the bot behind a webhook (Bale accepts ports 443 and 88, HTTPS only)."""

import os

from aiohttp import web

from balegram import Bot, Dispatcher
from balegram.filters import CommandStart
from balegram.types import Message
from balegram.webhook import SimpleRequestHandler, secret_path, setup_application

BASE_URL = os.environ["PUBLIC_URL"]  # e.g. https://bot.example.com
PATH = os.environ.get("WEBHOOK_PATH") or secret_path()  # keep it unguessable

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("webhook is working")


@dp.on_startup
async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_URL}{PATH}")


def main() -> None:
    bot = Bot(os.environ["BALE_TOKEN"])
    app = web.Application()
    SimpleRequestHandler(dp, bot).register(app, PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
