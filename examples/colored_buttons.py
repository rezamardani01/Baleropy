"""Colored inline buttons (Bale beta feature): green, red and blue via ``style=``."""

import asyncio

from baleropy import Bot, Dispatcher, F
from baleropy.filters import CommandStart
from baleropy.types import ButtonStyle, CallbackQuery, Message
from baleropy.utils import InlineKeyboardBuilder

# Get a token from @botfather (https://ble.ir/botfather) and paste it here.
TOKEN = "YOUR_BOT_TOKEN"

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="دکمه سبز", callback_data="green", style=ButtonStyle.SUCCESS)
    kb.button(text="دکمه قرمز", callback_data="red", style=ButtonStyle.DANGER)
    kb.button(text="دکمه آبی", callback_data="blue", style=ButtonStyle.PRIMARY)
    kb.button(text="دکمه معمولی", callback_data="plain")  # no style: the default look
    kb.adjust(2, 1, 1)
    await message.answer("تست دکمه‌های رنگی بله 🎨", reply_markup=kb.as_markup())


@dp.callback_query(F.data.in_({"green", "red", "blue", "plain"}))
async def pressed(query: CallbackQuery) -> None:
    await query.answer(f"روی {query.data} زدی")


async def main() -> None:
    await dp.start_polling(Bot(TOKEN), skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
