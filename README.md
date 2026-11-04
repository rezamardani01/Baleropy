# balegram

Modern, fully-typed, asynchronous framework for the [Bale](https://bale.ai) Bot API.
Routers, middlewares, composable filters, FSM and pydantic models, with an architecture
familiar to [aiogram](https://github.com/aiogram/aiogram) users.

- **Routers**: nest them freely to split a bot into modules.
- **Middlewares**: outer (every event) and inner (after a handler was chosen), class or function based, at update, router or event level. Outgoing request middlewares too.
- **Filters**: `F` magic filter (`F.a == F.b` too), `MagicData`, `Command`, `CallbackData`, `StateFilter`, chat/admin/membership filters, and your own. Combine with `&`, `|`, `~`. A filter can return a `dict` that is injected into the handler.
- **Dependency injection**: handlers just declare the arguments they want (`bot`, `state`, `event_from_user`, your own data...).
- **FSM**: states and groups, pluggable storage (memory, Redis), three isolation strategies.
- **Full Bot API coverage**: every method and type of the [Bale docs](https://docs.bale.ai), as typed method objects *and* `bot.*` shortcuts. Unknown fields never break parsing.
- **Polling and webhook** runners, 429 auto-retry, graceful shutdown.
- **Colored buttons** (`style=`), deep links, Markdown helpers, Business API, flood control.
- Python **3.10+**, strict `mypy`, tested on 3.10 and 3.15.
- 📘 **Full documentation (Persian + English): https://rezamardani01.github.io/balegram-docs/**

## Install

```bash
pip install balegram
# with Redis storage for the FSM
pip install "balegram[redis]"
```

Latest unreleased code: `pip install git+https://github.com/rezamardani01/balegram.git`

## Quick start

```python
import asyncio
from balegram import Bot, Dispatcher, F
from balegram.filters import CommandStart
from balegram.types import Message

TOKEN = "YOUR_BOT_TOKEN"  # get it from @botfather (https://ble.ir/botfather)

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Hello!")


@dp.message(F.text)
async def echo(message: Message):
    await message.reply(message.text)


asyncio.run(dp.start_polling(Bot(TOKEN), skip_updates=True))
```

## Routers

```python
from balegram import Router

shop = Router(name="shop")


@shop.message(Command("buy"))
async def buy(message: Message): ...


dp.include_router(shop)
```

Events are offered to the router's own handlers first, then to its sub-routers; the first matching
handler wins (raise `SkipHandler` to pass the event on).

## Middlewares

```python
from balegram.dispatcher import BaseMiddleware


class DbMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        async with pool.acquire() as db:
            data["db"] = db  # available as `db` in every handler
            return await handler(event, data)


dp.update.outer_middleware(DbMiddleware())  # every update
router.message.middleware(my_inner_mw)  # only when a message handler matched
```

Built in: `LoggingMiddleware`, `ThrottlingMiddleware`, `CallbackAnswerMiddleware`.
Raise `CancelHandler` inside a middleware to drop the event.

## Filters

```python
from balegram import F
from balegram.filters import Filter, Command, CallbackData, ChatTypeFilter


@router.message(F.text.startswith("!"), ChatTypeFilter("group"))
@router.message(Command("ban"), F.reply_to_message)
@router.message((F.text == "a") | (F.text == "b"))
class Product(CallbackData, prefix="prod"):
    id: int
    action: str


@router.callback_query(Product.filter(F.action == "buy"))
async def buy(query, callback_data: Product): ...


class IsPremium(Filter):  # custom filter
    async def __call__(self, event, db) -> bool | dict:
        user = await db.get_user(event.from_user.id)
        return {"user": user} if user.premium else False
```

## FSM

```python
from balegram.fsm import State, StatesGroup, FSMContext


class Form(StatesGroup):
    name = State()
    age = State()


@dp.message(Command("form"))
async def begin(message: Message, state: FSMContext):
    await state.set_state(Form.name)


@dp.message(Form.name)
async def name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(Form.age)
```

## Webhook

See [`examples/webhook_bot.py`](https://github.com/rezamardani01/balegram/blob/main/examples/webhook_bot.py). Bale webhooks need HTTPS on port 443 or 88
and send no secret header, so use `secret_path()` (or a `verify=` callback) to keep the URL private.

## Sending files

```python
from balegram.types import FSInputFile, BufferedInputFile

await bot.send_document(chat_id, FSInputFile("report.pdf"))
await bot.send_photo(chat_id, BufferedInputFile(data, "pic.png"), caption="hi")
await bot.send_photo(chat_id, "an_existing_file_id")
```

## Colored buttons

Bale's beta clients render `success` (green), `danger` (red) and `primary` (blue) buttons.
Older clients ignore `style` and show a normal button.

```python
from balegram.types import ButtonStyle
from balegram.utils import InlineKeyboardBuilder

kb = InlineKeyboardBuilder()
kb.button(text="Accept", callback_data="ok", style=ButtonStyle.SUCCESS)
kb.button(text="Reject", callback_data="no", style="danger")  # plain strings work too
kb.button(text="More", callback_data="more", style=ButtonStyle.PRIMARY)
await message.answer("Choose:", reply_markup=kb.adjust(2, 1).as_markup())
```

`ReplyKeyboardBuilder.button(..., style=...)` accepts the same argument (only inline buttons are
confirmed to render colors so far).

## Bot links, formatting and other helpers

```python
from balegram.utils import (
    ChatActionSender,
    MediaGroupBuilder,
    bold,
    italic,
    link,
    split_text,
    create_start_link,
)

url = await create_start_link(bot, "ref42")  # https://ble.ir/<bot>?start=ref42
# read it back:  @dp.message(CommandStart(deep_link=True))  ->  command.args == "ref42"

await message.answer(f"price: {bold('10')} rial, see {link('docs', 'https://docs.bale.ai')}")
for chunk in split_text(very_long_text):  # Bale allows 4096 characters per message
    await message.answer(chunk)

async with ChatActionSender.typing(bot, message.chat.id):  # "typing..." while this block runs
    answer = await slow_work()

album = MediaGroupBuilder(caption="Trip").add_photo(FSInputFile("a.jpg")).add_photo("file_id")
await bot.send_media_group(message.chat.id, album.build())
```

Bale formats every message as Markdown (`**bold**`, `__italic__`, `[label](url)`); the docs ask for a
space before the opening and after the closing bold/italic marker.

Documented limits are checked before a request leaves your machine (message text 1-4096, callback
answer text 200, media-group caption 1024, invoice title 32 / description 255 / payload 128 bytes,
sticker set name/title 64), so you get a clear `ValidationError` instead of an HTTP 400.

## Business API (bulk messaging)

```python
bot = Bot.business("TOKEN")  # https://tapi.bale.ai/business/bot<TOKEN>/...
await bot.send_message(private_chat_id, "Hello!")
```

Only `getMe`, `sendMessage`, `forwardMessage`, `sendPhoto`, `sendVideo`, `sendAudio` and
`sendDocument` exist there, `chat_id` must be a private chat and files are sent by `file_id` only.
Sending is billed from your Bale business account credit.

## Flood control

On HTTP 429 the session pauses *every* request of that bot for `retry_after` seconds and retries
(`AiohttpSession(retry_on_flood=60, max_flood_retries=5)`). `Dispatcher.start_polling` handles at
most `max_concurrent_updates=50` updates at once.

## Examples

[`examples/`](https://github.com/rezamardani01/balegram/tree/main/examples) holds a minimal bot, a modular bot (routers + middlewares + custom filter),
an FSM form, colored buttons and a webhook bot. Put your token in the `TOKEN` constant at the top
of each file. The examples are exercised by the test suite.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
ruff check . && mypy balegram && pytest
```

## Notes about Bale

- `answerCallbackQuery` is not supported by old clients; `CallbackQuery.answer()` skips them
  (detected by an id starting with `1`, as the Bale docs describe).
- Messages can only be deleted within 48 hours; the server keeps 2000 updates for 24 hours.
- Payments use the Bale wallet (`provider_token` for tests: `WALLET-TEST-1111111111111111`).

## License

MIT
