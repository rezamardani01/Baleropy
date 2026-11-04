from __future__ import annotations

import abc
from typing import Any

FilterResult = bool | dict[str, Any]


class Filter(abc.ABC):
    """Base class for custom filters.

    ``__call__`` receives the event plus every item of the middleware ``data`` as keyword
    arguments. Return ``False`` to reject, ``True`` to accept, or a ``dict`` to accept *and*
    inject extra keyword arguments into the handler.

    Filters combine with ``&``, ``|`` and ``~``.
    """

    @abc.abstractmethod
    async def __call__(self, event: Any, **data: Any) -> FilterResult: ...

    def __and__(self, other: Any) -> Filter:
        return _And(self, other)

    def __or__(self, other: Any) -> Filter:
        return _Or(self, other)

    def __invert__(self) -> Filter:
        return _Not(self)

    def __rand__(self, other: Any) -> Filter:
        return _And(other, self)

    def __ror__(self, other: Any) -> Filter:
        return _Or(other, self)


async def _run(flt: Any, event: Any, data: dict[str, Any]) -> FilterResult:
    # imported lazily: handler.py depends on this module
    from ..dispatcher.event.handler import CallableObject

    obj = flt if isinstance(flt, CallableObject) else CallableObject(flt, threaded=False)
    result: FilterResult = await obj.call(event, **data)
    return result


class _And(Filter):
    def __init__(self, *filters: Any) -> None:
        self.filters = filters

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        collected: dict[str, Any] = {}
        for flt in self.filters:
            result = await _run(flt, event, {**data, **collected})
            if not result:
                return False
            if isinstance(result, dict):
                collected.update(result)
        return collected or True


class _Or(Filter):
    def __init__(self, *filters: Any) -> None:
        self.filters = filters

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        for flt in self.filters:
            result = await _run(flt, event, data)
            if result:
                return result
        return False


class _Not(Filter):
    def __init__(self, target: Any) -> None:
        self.target = target

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        return not await _run(self.target, event, data)
