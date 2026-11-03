"""Smallest possible bot: greets on /start and echoes everything else."""

import asyncio
import os

from balegram import Bot, Dispatcher, F
from balegram.filters import CommandStart
from balegram.types import Message

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(f"سلام {message.from_user.full_name if message.from_user else ''}!")


@dp.message(F.text)
async def echo(message: Message) -> None:
    await message.reply(message.text or "")


async def main() -> None:
    bot = Bot(os.environ["BALE_TOKEN"])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
