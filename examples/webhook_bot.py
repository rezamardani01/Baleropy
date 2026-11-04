"""Run the bot behind a webhook (Bale accepts ports 443 and 88, HTTPS only)."""

from aiohttp import web

from balegram import Bot, Dispatcher
from balegram.filters import CommandStart
from balegram.types import Message
from balegram.webhook import SimpleRequestHandler, setup_application

# Get a token from @botfather (https://ble.ir/botfather) and paste it here.
# Never commit a real token to a public repository.
TOKEN = "YOUR_BOT_TOKEN"

# Public HTTPS address of your server (Bale supports ports 443 and 88).
BASE_URL = "https://bot.example.com"
# Keep the path unguessable: Bale sends no secret header. Generate it once and keep it:
#   python -c "from balegram.webhook import secret_path; print(secret_path())"
PATH = "/webhook/CHANGE_ME"

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("webhook is working")


@dp.on_startup
async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(f"{BASE_URL}{PATH}")


def main() -> None:
    bot = Bot(TOKEN)
    app = web.Application()
    SimpleRequestHandler(dp, bot).register(app, PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
