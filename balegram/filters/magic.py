from __future__ import annotations

import operator
import re
from collections.abc import Callable, Container
from typing import Any

from .base import Filter, FilterResult

_MISSING = object()


class _RootStep:
    """A step that also needs the original object (to compare two magic expressions)."""

    def __init__(self, function: Callable[[Any, Any], Any]) -> None:
        self.function = function


class MagicFilter(Filter):
    """Declarative filters: ``F.text == "hi"``, ``F.from_user.id.in_({1, 2})``, ``F.photo``.

    Every attribute access / operator records a step. When the filter runs, the steps are applied
    to the event; any failing step (missing attribute, wrong type) makes the whole filter falsy.
    Non-boolean truthy results (e.g. a ``regexp`` match) are injected as ``magic_result``.
    """

    __slots__ = ("_steps",)

    def __init__(self, steps: tuple[Callable[[Any], Any] | _RootStep, ...] = ()) -> None:
        self._steps = steps

    def _then(self, step: Callable[[Any], Any]) -> MagicFilter:
        return MagicFilter((*self._steps, step))

    def resolve(self, value: Any) -> Any:
        """Apply the recorded steps. Returns ``None`` if a step cannot be applied."""
        root = value
        try:
            for step in self._steps:
                value = step.function(value, root) if isinstance(step, _RootStep) else step(value)
        except (AttributeError, TypeError, KeyError, IndexError, ValueError):
            return None
        return value

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        result = self.resolve(event)
        if not result:
            return False
        if result is True:
            return True
        return {"magic_result": result}

    def __repr__(self) -> str:
        return f"<MagicFilter steps={len(self._steps)}>"

    # --- navigation ------------------------------------------------------------------------
    def __getattr__(self, name: str) -> MagicFilter:
        if name.startswith("__"):
            raise AttributeError(name)
        return self._then(lambda v: getattr(v, name, None))

    def __getitem__(self, key: Any) -> MagicFilter:
        return self._then(lambda v: v[key])

    # --- comparison ------------------------------------------------------------------------
    def _compare(self, other: Any, op: Callable[[Any, Any], Any]) -> MagicFilter:
        if isinstance(other, MagicFilter):  # F.a == F.b compares two values of the same object
            return MagicFilter(
                (*self._steps, _RootStep(lambda value, root: op(value, other.resolve(root))))
            )
        return self._then(lambda value: op(value, other))

    def __eq__(self, other: object) -> MagicFilter:  # type: ignore[override]
        return self._compare(other, operator.eq)

    def __ne__(self, other: object) -> MagicFilter:  # type: ignore[override]
        return self._compare(other, operator.ne)

    def __lt__(self, other: Any) -> MagicFilter:
        return self._compare(other, operator.lt)

    def __le__(self, other: Any) -> MagicFilter:
        return self._compare(other, operator.le)

    def __gt__(self, other: Any) -> MagicFilter:
        return self._compare(other, operator.gt)

    def __ge__(self, other: Any) -> MagicFilter:
        return self._compare(other, operator.ge)

    __hash__ = object.__hash__

    # --- helpers ---------------------------------------------------------------------------
    def in_(self, values: Container[Any]) -> MagicFilter:
        return self._then(lambda v: v in values)

    def not_in(self, values: Container[Any]) -> MagicFilter:
        return self._then(lambda v: v not in values)

    def contains(self, item: Any) -> MagicFilter:
        return self._then(lambda v: item in v)

    def startswith(
        self, prefix: str | tuple[str, ...], *, ignore_case: bool = False
    ) -> MagicFilter:
        if ignore_case:
            prefixes = (prefix,) if isinstance(prefix, str) else prefix
            lowered = tuple(p.lower() for p in prefixes)
            return self._then(lambda v: v.lower().startswith(lowered))
        return self._then(lambda v: v.startswith(prefix))

    def endswith(self, suffix: str | tuple[str, ...], *, ignore_case: bool = False) -> MagicFilter:
        if ignore_case:
            suffixes = (suffix,) if isinstance(suffix, str) else suffix
            lowered = tuple(s.lower() for s in suffixes)
            return self._then(lambda v: v.lower().endswith(lowered))
        return self._then(lambda v: v.endswith(suffix))

    def lower(self) -> MagicFilter:
        return self._then(lambda v: v.lower())

    def len(self) -> MagicFilter:
        return self._then(lambda v: len(v))

    def is_(self, other: Any) -> MagicFilter:
        return self._then(lambda v: v is other)

    def is_not(self, other: Any) -> MagicFilter:
        return self._then(lambda v: v is not other)

    def regexp(self, pattern: str | re.Pattern[str], flags: int = 0) -> MagicFilter:
        compiled = pattern if isinstance(pattern, re.Pattern) else re.compile(pattern, flags)
        return self._then(lambda v: compiled.search(v))

    def func(self, function: Callable[[Any], Any]) -> MagicFilter:
        return self._then(function)

    def as_(self, name: str) -> Filter:
        """Inject the resolved value under ``name`` (only if truthy)."""
        magic = self

        class _As(Filter):
            async def __call__(self, event: Any, **data: Any) -> FilterResult:
                value = magic.resolve(event)
                return {name: value} if value else False

        return _As()

    # make `not F.x` impossible to misuse silently
    def __bool__(self) -> bool:
        raise TypeError("MagicFilter cannot be used as a boolean, use & | ~ instead")


F = MagicFilter()
