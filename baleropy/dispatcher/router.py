from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from .event.bases import UNHANDLED, Data
from .event.handler import CallableObject
from .event.observer import EventObserver
from .middlewares.base import wrap_middlewares

EVENT_TYPES = (
    "message",
    "edited_message",
    "callback_query",
    "pre_checkout_query",
    "unknown",
    "error",
)


class Router:
    """Groups handlers. Routers nest: include sub-routers to build modular bots."""

    def __init__(self, *, name: str | None = None) -> None:
        self.name = name or hex(id(self))
        self._parent: Router | None = None
        self.sub_routers: list[Router] = []

        self.message = EventObserver(self, "message")
        self.edited_message = EventObserver(self, "edited_message")
        self.callback_query = EventObserver(self, "callback_query")
        self.pre_checkout_query = EventObserver(self, "pre_checkout_query")
        self.unknown = EventObserver(self, "unknown")
        self.error = EventObserver(self, "error")
        self.observers: dict[str, EventObserver] = {
            "message": self.message,
            "edited_message": self.edited_message,
            "callback_query": self.callback_query,
            "pre_checkout_query": self.pre_checkout_query,
            "unknown": self.unknown,
            "error": self.error,
        }
        self.startup_callbacks: list[CallableObject] = []
        self.shutdown_callbacks: list[CallableObject] = []

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name!r}>"

    # --- tree ------------------------------------------------------------------------------
    @property
    def parent_router(self) -> Router | None:
        return self._parent

    @parent_router.setter
    def parent_router(self, router: Router) -> None:
        if self._parent is not None:
            raise RuntimeError(f"{self!r} is already attached to {self._parent!r}")
        if router is self:
            raise RuntimeError("A router cannot include itself")
        node: Router | None = router
        while node is not None:
            if node is self:
                raise RuntimeError("Circular router inclusion detected")
            node = node._parent
        self._parent = router

    @property
    def chain_head(self) -> Iterator[Router]:
        """Routers from the root down to ``self``."""
        chain: list[Router] = []
        node: Router | None = self
        while node is not None:
            chain.append(node)
            node = node._parent
        return reversed(chain)

    @property
    def chain_tail(self) -> Iterator[Router]:
        """``self`` followed by every descendant (depth first)."""
        yield self
        for router in self.sub_routers:
            yield from router.chain_tail

    def include_router(self, router: Router) -> Router:
        if not isinstance(router, Router):
            raise ValueError(f"router should be an instance of Router, got {type(router)}")
        router.parent_router = self
        self.sub_routers.append(router)
        return router

    def include_routers(self, *routers: Router) -> None:
        for router in routers:
            self.include_router(router)

    # --- lifecycle -------------------------------------------------------------------------
    def on_startup(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        self.startup_callbacks.append(CallableObject(callback))
        return callback

    def on_shutdown(self, callback: Callable[..., Any]) -> Callable[..., Any]:
        self.shutdown_callbacks.append(CallableObject(callback))
        return callback

    async def emit_startup(self, **kwargs: Any) -> None:
        for router in self.chain_tail:
            for cb in router.startup_callbacks:
                await cb.call(**kwargs)

    async def emit_shutdown(self, **kwargs: Any) -> None:
        for router in reversed(list(self.chain_tail)):
            for cb in router.shutdown_callbacks:
                await cb.call(**kwargs)

    # --- propagation -----------------------------------------------------------------------
    async def propagate_event(self, event_type: str, event: Any, **kwargs: Any) -> Any:
        observer = self.observers[event_type]

        async def run(ev: Any, data: Data) -> Any:
            result = await observer.trigger(ev, **data)
            if result is not UNHANDLED:
                return result
            for router in self.sub_routers:
                result = await router.propagate_event(event_type, ev, **data)
                if result is not UNHANDLED:
                    return result
            return UNHANDLED

        wrapped = wrap_middlewares(observer.outer_middlewares, run)
        return await wrapped(event, {**kwargs, "event_router": self})
