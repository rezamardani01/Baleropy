from __future__ import annotations

import abc
from collections.abc import Callable, Sequence
from functools import partial
from typing import Any

from ..event.bases import Data, MiddlewareType, NextHandler


class BaseMiddleware(abc.ABC):
    """Class-based middleware.

    ``handler`` is the next step of the chain; call it (or don't) to continue (or cancel).
    ``data`` is the shared context dict that ends up as handler keyword arguments.
    """

    @abc.abstractmethod
    async def __call__(self, handler: NextHandler, event: Any, data: Data) -> Any: ...


async def _call_middleware(
    middleware: MiddlewareType, nxt: NextHandler, event: Any, data: Data
) -> Any:
    return await middleware(nxt, event, data)


def wrap_middlewares(middlewares: Sequence[MiddlewareType], handler: NextHandler) -> NextHandler:
    """Fold middlewares around ``handler`` so that the first registered runs outermost."""
    chain: Callable[[Any, Data], Any] = handler
    for middleware in reversed(middlewares):
        chain = partial(_call_middleware, middleware, chain)
    return chain
