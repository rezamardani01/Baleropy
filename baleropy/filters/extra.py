from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any

from .base import Filter, FilterResult
from .magic import MagicFilter


class MagicData(Filter):
    """Magic filter applied to the handler *data* instead of the event.

    >>> @router.message(MagicData(F.is_admin))                  # a value put there by a middleware
    >>> @router.message(MagicData(F.event_from_user.id == F.config.owner_id))
    """

    def __init__(self, magic: MagicFilter) -> None:
        self.magic = magic

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        return bool(self.magic.resolve(SimpleNamespace(event=event, **data)))


class ExceptionTypeFilter(Filter):
    """For ``@router.error()``: matches when the exception is an instance of the given types."""

    def __init__(self, *exceptions: type[BaseException]) -> None:
        if not exceptions:
            raise ValueError("ExceptionTypeFilter needs at least one exception type")
        self.exceptions = exceptions

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        exception = getattr(event, "exception", None)
        return isinstance(exception, self.exceptions)


class ExceptionMessageFilter(Filter):
    """For ``@router.error()``: matches when the exception text matches a regular expression."""

    def __init__(self, pattern: str | re.Pattern[str]) -> None:
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        exception = getattr(event, "exception", None)
        if exception is None:
            return False
        match = self.pattern.search(str(exception))
        return {"match_exception": match} if match else False
