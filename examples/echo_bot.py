"""Smallest possible bot: greets on /start and echoes everything else."""

from baleropy import Bot, Dispatcher, F
from baleropy.filters import CommandStart
from baleropy.types import Message

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


if __name__ == "__main__":
    dp.run_polling(Bot(TOKEN), skip_updates=True)
