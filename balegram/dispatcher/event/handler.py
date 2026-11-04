from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from functools import partial
from typing import Any

from ...filters.base import FilterResult


class CallableObject:
    """Wraps any callable and passes it only the keyword arguments it declares (DI)."""

    def __init__(self, callback: Callable[..., Any], threaded: bool = True) -> None:
        self.callback = callback
        self.threaded = threaded
        target = (
            callback
            if inspect.isroutine(callback) or isinstance(callback, partial)
            else callback.__call__  # type: ignore[operator]
        )
        signature = inspect.signature(target)
        kinds = (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        self.params = {n for n, p in signature.parameters.items() if p.kind in kinds}
        positional = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.positional_names = [n for n, p in signature.parameters.items() if p.kind in positional]
        self.accepts_varargs = any(
            p.kind is inspect.Parameter.VAR_POSITIONAL for p in signature.parameters.values()
        )
        self.accepts_any = any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()
        )
        self.awaitable = inspect.iscoroutinefunction(target) or inspect.iscoroutinefunction(
            callback
        )

    def prepare_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        if self.accepts_any:
            return kwargs
        return {k: v for k, v in kwargs.items() if k in self.params}

    def prepare_args(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[Any, ...]:
        """Pass the event positionally only if the callback has a free first parameter."""
        if not args or self.accepts_varargs:
            return args
        if not self.positional_names or self.positional_names[0] in kwargs:
            return ()
        return args[: len(self.positional_names)]

    async def call(self, *args: Any, **kwargs: Any) -> Any:
        if args and "event" not in kwargs:
            kwargs["event"] = args[0]  # a parameter named `event` always receives the event
        args = self.prepare_args(args, kwargs)
        call = partial(self.callback, *args, **self.prepare_kwargs(kwargs))
        if self.awaitable:
            return await call()
        if self.threaded:
            return await asyncio.to_thread(call)
        result = call()
        if inspect.isawaitable(result):
            return await result
        return result


class HandlerObject(CallableObject):
    def __init__(
        self,
        callback: Callable[..., Any],
        filters: list[Any] | None = None,
        flags: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(callback, threaded=True)
        self.filters = [CallableObject(f, threaded=False) for f in filters or []]
        self.flags = flags or {}

    async def check(self, event: Any, **data: Any) -> tuple[bool, dict[str, Any]]:
        """Run the filters in order. Returns ``(passed, extra_kwargs_from_filters)``."""
        extra: dict[str, Any] = {}
        for flt in self.filters:
            result: FilterResult = await flt.call(event, **data, **extra)
            if not result:
                return False, {}
            if isinstance(result, dict):
                extra.update(result)
        return True, extra
