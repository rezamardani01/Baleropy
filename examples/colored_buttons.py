"""Colored inline buttons (Bale beta feature): green, red and blue via ``style=``."""

from baleropy import Bot, Button, Dispatcher, F
from baleropy.filters import CommandStart
from baleropy.types import ButtonStyle, CallbackQuery, Message

# Get a token from @botfather (https://ble.ir/botfather) and paste it here.
TOKEN = "YOUR_BOT_TOKEN"

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    buttons = [
        [
            Button.inline("دکمه سبز", "green", style=ButtonStyle.SUCCESS),
            Button.inline("دکمه قرمز", "red", style=ButtonStyle.DANGER),
        ],
        [Button.inline("دکمه آبی", "blue", style=ButtonStyle.PRIMARY)],
        [Button.inline("دکمه معمولی", "plain")],
    ]
    await message.answer("تست دکمه‌های رنگی بله 🎨", buttons=buttons)


@dp.callback_query(F.data.in_({"green", "red", "blue", "plain"}))
async def pressed(query: CallbackQuery) -> None:
    await query.answer(f"روی {query.data} زدی")


if __name__ == "__main__":
    dp.run_polling(Bot(TOKEN), skip_updates=True)
