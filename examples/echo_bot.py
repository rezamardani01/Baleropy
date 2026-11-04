"""Smallest possible bot: greets on /start and echoes everything else."""

import asyncio

from balegram import Bot, Dispatcher, F
from balegram.filters import CommandStart
from balegram.types import Message

# Get a token from @botfather (https://ble.ir/botfather) and paste it here.
# Never commit a real token to a public repository.
TOKEN = "YOUR_BOT_TOKEN"

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(f"سلام {message.from_user.full_name if message.from_user else ''}!")


@dp.message(F.text)
async def echo(message: Message) -> None:
    await message.reply(message.text or "")


async def main() -> None:
    bot = Bot(TOKEN)
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Ctrl+C
