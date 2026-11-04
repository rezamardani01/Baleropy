from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from ...types import Update


class _Unhandled:
    """Sentinel returned when no handler took the event."""

    def __repr__(self) -> str:
        return "UNHANDLED"

    def __bool__(self) -> bool:
        return False


UNHANDLED = _Unhandled()

Data = dict[str, Any]
NextHandler = Callable[[Any, Data], Awaitable[Any]]
MiddlewareType = Callable[[NextHandler, Any, Data], Awaitable[Any]]


@dataclass
class ErrorEvent:
    """What ``@router.error()`` handlers receive."""

    update: Update
    exception: Exception
