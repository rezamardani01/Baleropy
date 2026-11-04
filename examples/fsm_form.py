"""Multi-step conversation with the finite state machine."""

import asyncio

from baleropy import Bot, Dispatcher, F
from baleropy.filters import Command
from baleropy.fsm import FSMContext, MemoryStorage, State, StatesGroup
from baleropy.types import Message

# Get a token from @botfather (https://ble.ir/botfather) and paste it here.
# Never commit a real token to a public repository.
TOKEN = "YOUR_BOT_TOKEN"

dp = Dispatcher(storage=MemoryStorage())


class Form(StatesGroup):
    name = State()
    age = State()


@dp.message(Command("form"))
async def begin(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.name)
    await message.answer("اسمتان چیست؟")


@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("لغو شد")


@dp.message(Form.name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(Form.age)
    await message.answer("سنتان؟")


@dp.message(Form.age, F.text.regexp(r"^\d{1,3}$"))
async def got_age(message: Message, state: FSMContext) -> None:
    data = await state.update_data(age=int(message.text or 0))
    await state.clear()
    await message.answer(f"ثبت شد: {data['name']} ({data['age']} ساله)")


@dp.message(Form.age)
async def bad_age(message: Message) -> None:
    await message.answer("لطفاً عدد وارد کنید")


async def main() -> None:
    await dp.start_polling(Bot(TOKEN), skip_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
