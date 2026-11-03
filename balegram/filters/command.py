from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..types import Message
from .base import Filter, FilterResult

if TYPE_CHECKING:
    from ..client.bot import Bot


@dataclass
class CommandObject:
    """Parsed command, injected as ``command`` into the handler."""

    prefix: str = "/"
    command: str = ""
    mention: str | None = None
    args: str | None = None

    @property
    def text(self) -> str:
        mention = f"@{self.mention}" if self.mention else ""
        args = f" {self.args}" if self.args else ""
        return f"{self.prefix}{self.command}{mention}{args}"

    @property
    def args_list(self) -> list[str]:
        return self.args.split() if self.args else []


class Command(Filter):
    """Matches ``/command args`` messages and injects a :class:`CommandObject`.

    ``magic`` may be any filter (typically ``F.args``) evaluated on the parsed command.
    """

    def __init__(
        self,
        *commands: str | re.Pattern[str],
        prefix: str = "/",
        ignore_case: bool = False,
        ignore_mention: bool = False,
        magic: Any = None,
    ) -> None:
        if not commands:
            raise ValueError("Command filter needs at least one command")
        self.commands = tuple(
            c if isinstance(c, re.Pattern) else (c.lower() if ignore_case else c) for c in commands
        )
        self.prefix = prefix
        self.ignore_case = ignore_case
        self.ignore_mention = ignore_mention
        self.magic = magic

    def parse(self, text: str) -> CommandObject | None:
        if not text.startswith(self.prefix):
            return None
        head, _, rest = text[len(self.prefix) :].partition(" ")
        head, _, tail = head.partition("\n")
        if tail:  # command followed by a newline instead of a space
            rest = f"{tail} {rest}".strip()
        name, _, mention = head.partition("@")
        return CommandObject(
            prefix=self.prefix,
            command=name,
            mention=mention or None,
            args=rest.strip() or None,
        )

    def _matches(self, name: str) -> bool:
        candidate = name.lower() if self.ignore_case else name
        for command in self.commands:
            if isinstance(command, re.Pattern):
                if command.fullmatch(candidate):
                    return True
            elif command == candidate:
                return True
        return False

    async def __call__(self, event: Any, bot: Bot | None = None, **data: Any) -> FilterResult:
        if not isinstance(event, Message) or not event.text:
            return False
        command = self.parse(event.text)
        if command is None or not self._matches(command.command):
            return False
        if command.mention and not self.ignore_mention:
            if bot is None:
                return False
            me = await bot.me()
            if (me.username or "").lower() != command.mention.lower():
                return False
        if self.magic is not None:
            result = self.magic.resolve(command) if hasattr(self.magic, "resolve") else None
            if not result:
                return False
        return {"command": command}


class CommandStart(Command):
    """``/start`` with optional deep-link support (``ble.ir/bot?start=payload``)."""

    def __init__(self, *, deep_link: bool = False, encoded: bool = False, **kwargs: Any) -> None:
        super().__init__("start", **kwargs)
        self.deep_link = deep_link
        self.encoded = encoded

    async def __call__(self, event: Any, bot: Bot | None = None, **data: Any) -> FilterResult:
        result = await super().__call__(event, bot=bot, **data)
        if not isinstance(result, dict):
            return result
        command: CommandObject = result["command"]
        if self.deep_link and not command.args:
            return False
        if self.encoded and command.args:
            try:
                padded = command.args + "=" * (-len(command.args) % 4)
                command.args = base64.urlsafe_b64decode(padded).decode()
            except (ValueError, UnicodeDecodeError):
                return False
        return result
