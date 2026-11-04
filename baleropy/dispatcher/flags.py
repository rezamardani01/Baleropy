"""Handler flags: static metadata attached when registering, readable from middlewares.

>>> @router.message(Command("buy"), rate_limit=5)        # any keyword becomes a flag
>>> ...
>>> async def mw(handler, event, data):
...     seconds = get_flag(data, "rate_limit", default=1)
"""

from __future__ import annotations

from typing import Any


def get_flag(data: dict[str, Any], name: str, default: Any = None) -> Any:
    """Value of flag ``name`` of the handler selected for this event (inner middlewares only)."""
    handler = data.get("handler")
    if handler is None:
        return default
    return handler.flags.get(name, default)
