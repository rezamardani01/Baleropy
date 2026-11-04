"""Text helpers for Bale's Markdown flavour.

Bale formats every message as Markdown: ``**bold**``, ``__italic__`` and ``[label](url)``.
Per the Bale docs, bold/italic markers need a space before the opening and after the closing pair,
so put these helpers between spaces: ``f"price: {bold('10')} rial"``.
"""

from __future__ import annotations

MAX_MESSAGE_LENGTH = 4096


def bold(text: str) -> str:
    return f"**{text}**"


def italic(text: str) -> str:
    return f"__{text}__"


def link(label: str, url: str) -> str:
    """``[label](url)`` (no space may separate the two parts)."""
    return f"[{label}]({url})"


def split_text(text: str, limit: int = MAX_MESSAGE_LENGTH) -> list[str]:
    """Split ``text`` into chunks of at most ``limit`` characters.

    Chunks break at a newline when possible, then at a space, and only as a last resort in the
    middle of a word. Use it for answers that may exceed Bale's 4096 character message limit.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    chunks: list[str] = []
    rest = text
    while len(rest) > limit:
        window = rest[: limit + 1]
        cut = window.rfind("\n")
        if cut < limit // 2:
            cut = window.rfind(" ")
        if cut < limit // 2:
            cut = limit
        chunks.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip("\n ") if cut != limit else rest[cut:]
    if rest or not chunks:
        chunks.append(rest.rstrip() if chunks else rest)
    return [chunk for chunk in chunks if chunk]
