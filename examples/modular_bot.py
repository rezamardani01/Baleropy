"""Routers, middlewares and custom filters working together."""

import logging
from typing import Any

from baleropy import Bot, Dispatcher, F, Router
from baleropy.dispatcher import BaseMiddleware
from baleropy.dispatcher.middlewares import LoggingMiddleware, ThrottlingMiddleware
from baleropy.filters import CallbackData, Command, Filter
from baleropy.types import CallbackQuery, Message
from baleropy.utils import InlineKeyboardBuilder

# Get a token from @botfather (https://ble.ir/botfather) and paste it here.
# Never commit a real token to a public repository.
TOKEN = "YOUR_BOT_TOKEN"

ADMINS = {123456789}  # numeric ids of the admins (ask your bot: /myid)


# --- custom filter: returns a dict -> injected into the handler as keyword arguments ---------
class HasWords(Filter):
    def __init__(self, minimum: int) -> None:
        self.minimum = minimum

    async def __call__(self, event: Any, **data: Any) -> bool | dict[str, Any]:
        words = (getattr(event, "text", None) or "").split()
        return {"words": words} if len(words) >= self.minimum else False


# --- custom middleware: puts a flag into the data every handler can receive -----------------
class AdminFlagMiddleware(BaseMiddleware):
    async def __call__(self, handler: Any, event: Any, data: dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        data["is_admin"] = bool(user and user.id in ADMINS)
        return await handler(event, data)


class Vote(CallbackData, prefix="vote"):
    option: str


# --- feature routers ---------------------------------------------------------------------------
polls = Router(name="polls")


@polls.message(Command("poll"))
async def poll(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="👍", callback_data=Vote(option="yes"))
    kb.button(text="👎", callback_data=Vote(option="no"))
    await message.answer("نظر شما؟", reply_markup=kb.as_markup())


@polls.callback_query(Vote.filter(F.option == "yes"))
async def voted_yes(query: CallbackQuery, callback_data: Vote) -> None:
    await query.answer(f"رأی شما ثبت شد: {callback_data.option}")


@polls.callback_query(Vote.filter())
async def voted_other(query: CallbackQuery, callback_data: Vote) -> None:
    await query.answer(f"رأی شما ثبت شد: {callback_data.option}", show_alert=True)


admin = Router(name="admin")
admin.message.filter(lambda message, is_admin=False: is_admin)  # router-level filter


@admin.message(Command("stats"))
async def stats(message: Message) -> None:
    await message.answer("آمار فقط برای ادمین‌ها")


common = Router(name="common")


@common.message(HasWords(3))
async def long_text(message: Message, words: list[str]) -> None:
    await message.answer(f"{len(words)} کلمه فرستادید")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    dp = Dispatcher()
    dp.update.outer_middleware(AdminFlagMiddleware())
    dp.message.outer_middleware(LoggingMiddleware())
    dp.message.outer_middleware(ThrottlingMiddleware(rate=0.5))
    dp.include_routers(polls, admin, common)
    dp.run_polling(Bot(TOKEN), skip_updates=True)


if __name__ == "__main__":
    main()
