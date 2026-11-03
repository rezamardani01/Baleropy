from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from ...exceptions import SkipHandler
from ..middlewares.base import wrap_middlewares
from .bases import UNHANDLED, Data, MiddlewareType
from .handler import CallableObject, HandlerObject

if TYPE_CHECKING:
    from ..router import Router

CB = TypeVar("CB", bound=Callable[..., Any])


class EventObserver:
    """Holds the handlers (plus middlewares and shared filters) of one event type of a router."""

    def __init__(self, router: Router, event_name: str) -> None:
        self.router = router
        self.event_name = event_name
        self.handlers: list[HandlerObject] = []
        self.filters: list[CallableObject] = []
        self.middlewares: list[MiddlewareType] = []
        self.outer_middlewares: list[MiddlewareType] = []

    def __repr__(self) -> str:
        return f"<EventObserver {self.event_name!r} handlers={len(self.handlers)}>"

    # --- registration ----------------------------------------------------------------------
    def filter(self, *filters: Any) -> None:
        """Filters applied to *every* handler of this observer (router-level filters)."""
        self.filters.extend(CallableObject(f, threaded=False) for f in filters)

    def middleware(self, middleware: MiddlewareType) -> MiddlewareType:
        """Inner middleware: runs only after a handler was selected (filters passed)."""
        self.middlewares.append(middleware)
        return middleware

    def outer_middleware(self, middleware: MiddlewareType) -> MiddlewareType:
        """Outer middleware: runs for every event of this type, before filters are evaluated."""
        self.outer_middlewares.append(middleware)
        return middleware

    def register(
        self, callback: Callable[..., Any], *filters: Any, **flags: Any
    ) -> Callable[..., Any]:
        self.handlers.append(HandlerObject(callback, list(filters), flags))
        return callback

    def __call__(self, *filters: Any, **flags: Any) -> Callable[[CB], CB]:
        def decorator(callback: CB) -> CB:
            self.register(callback, *filters, **flags)
            return callback

        return decorator

    # --- dispatching -----------------------------------------------------------------------
    def _inner_middlewares(self) -> list[MiddlewareType]:
        # parent routers' inner middlewares wrap the child's, outermost first
        chain: list[MiddlewareType] = []
        for router in self.router.chain_head:
            chain.extend(router.observers[self.event_name].middlewares)
        return chain

    async def trigger(self, event: Any, **data: Any) -> Any:
        """Find the first matching handler and run it (inside inner middlewares)."""
        for shared in self.filters:
            if not await shared.call(event, **data):
                return UNHANDLED
        for handler in self.handlers:
            passed, extra = await handler.check(event, **data)
            if not passed:
                continue
            handler_data: Data = {**data, **extra, "handler": handler}

            async def final(ev: Any, d: Data, _h: HandlerObject = handler) -> Any:
                return await _h.call(ev, **d)

            wrapped = wrap_middlewares(self._inner_middlewares(), final)
            try:
                return await wrapped(event, handler_data)
            except SkipHandler:
                continue
        return UNHANDLED
