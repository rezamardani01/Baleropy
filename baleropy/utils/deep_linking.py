"""Bot links: ``https://ble.ir/<bot_username>?start=<payload>``.

Opening the link starts the bot and sends ``/start <payload>``; read it with
``CommandStart(deep_link=True)`` (``encoded=True`` if you used ``encode=True`` here).
"""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from ..client.bot import Bot

BALE_DOMAIN = "ble.ir"


def encode_payload(payload: str) -> str:
    """URL-safe base64 without padding, so any text can travel in a link."""
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_payload(encoded: str) -> str:
    padded = encoded + "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(padded).decode()


def bot_link(username: str, payload: str | None = None, *, encode: bool = False) -> str:
    """Build the link from a username (with or without ``@``)."""
    link = f"https://{BALE_DOMAIN}/{username.lstrip('@')}"
    if payload is None:
        return link
    value = encode_payload(payload) if encode else payload
    return f"{link}?start={quote(value, safe='')}"


async def create_start_link(bot: Bot, payload: str | None = None, *, encode: bool = False) -> str:
    """Link that opens *this* bot (its username comes from ``getMe``)."""
    me = await bot.me()
    if not me.username:
        raise ValueError("The bot has no username, a link cannot be built")
    return bot_link(me.username, payload, encode=encode)
