from __future__ import annotations

from typing import Any, ClassVar

from ..filters.base import Filter, FilterResult


class State(Filter):
    """One state of a conversation. Usable directly as a handler filter."""

    def __init__(self, state: str | None = None, group_name: str | None = None) -> None:
        self._state = state
        self._group_name = group_name
        self._group: type[StatesGroup] | None = None

    @property
    def group(self) -> type[StatesGroup] | None:
        return self._group

    @property
    def state(self) -> str | None:
        if self._state is None or self._state == "*":
            return self._state
        group = self._group_name or (self._group.__full_group_name__ if self._group else "@")
        return f"{group}:{self._state}"

    def set_parent(self, group: type[StatesGroup]) -> None:
        self._group = group

    def __set_name__(self, owner: type, name: str) -> None:
        if self._state is None:
            self._state = name

    def __str__(self) -> str:
        return f"<State '{self.state}'>"

    __repr__ = __str__

    def __eq__(self, other: object) -> bool:
        if isinstance(other, State):
            return self.state == other.state
        if isinstance(other, str):
            return self.state == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.state)

    async def __call__(self, event: Any, raw_state: str | None = None, **data: Any) -> FilterResult:
        if self._state == "*":
            return True
        return raw_state == self.state


class StatesGroupMeta(type):
    __full_group_name__: str
    __states__: tuple[State, ...]
    __children__: tuple[type[StatesGroup], ...]

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any
    ) -> StatesGroupMeta:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        children: tuple[Any, ...] = tuple(
            v for v in namespace.values() if isinstance(v, type) and isinstance(v, StatesGroupMeta)
        )
        states = tuple(v for v in namespace.values() if isinstance(v, State))
        cls.__children__ = children
        cls.__states__ = states
        cls.__full_group_name__ = name
        for child in children:
            child.__full_group_name__ = f"{name}.{child.__name__}"
        for state in states:
            state.set_parent(cls)  # type: ignore[arg-type]
        return cls

    @property
    def __all_states__(cls) -> tuple[State, ...]:
        result = list(cls.__states__)
        for child in cls.__children__:
            result.extend(child.__all_states__)
        return tuple(result)

    @property
    def __all_states_names__(cls) -> tuple[str, ...]:
        return tuple(s.state for s in cls.__all_states__ if s.state)

    def __contains__(cls, item: object) -> bool:
        if isinstance(item, State):
            return item in cls.__all_states__
        if isinstance(item, str):
            return item in cls.__all_states_names__
        return False


class StatesGroup(metaclass=StatesGroupMeta):
    """Declare conversation states as class attributes.

    >>> class Form(StatesGroup):
    ...     name = State()
    ...     age = State()
    """

    __slots__: ClassVar[tuple[str, ...]] = ()


default_state = State()
any_state = State("*")
