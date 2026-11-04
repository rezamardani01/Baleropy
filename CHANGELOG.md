# Changelog

## 0.2.0

- Colored buttons: `style` on inline/reply buttons (`ButtonStyle`), `style=` in the keyboard builders.
- Chat ids are always sent as strings (Bale rejects an integer `chat_id` on `sendChatAction`).
- 429 handling: retry by default, one pause shared by all requests of a bot, bounded attempts.
- `Dispatcher.start_polling(max_concurrent_updates=...)`; API errors are logged as one line.
- Documented length limits are validated client-side.
- New helpers: deep links, Markdown helpers, `split_text`, `ChatActionSender`, `MediaGroupBuilder`,
  `InlineKeyboardBuilder.from_markup/copy`, `Bot.business()`.
- New filters: `MagicData`, `ExceptionTypeFilter`, `ExceptionMessageFilter`; `F.a == F.b`; `get_flag`.
- A handler parameter named `event` always receives the event.
- `Message.reply_markup` no longer drops an update when Bale sends an unexpected shape.

## 0.1.0

First release: Bot API client, routers, middlewares, filters, FSM, polling and webhook.
