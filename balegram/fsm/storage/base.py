from __future__ import annotations

import abc
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..state import State

StateType = State | str | None


@dataclass(frozen=True)
class StorageKey:
    bot_id: int
    chat_id: int
    user_id: int


def state_to_str(state: StateType) -> str | None:
    return state.state if isinstance(state, State) else state


class BaseStorage(abc.ABC):
    """Persistence backend of the FSM. Implement these five coroutines for a custom one."""

    @abc.abstractmethod
    async def set_state(self, key: StorageKey, state: StateType = None) -> None: ...

    @abc.abstractmethod
    async def get_state(self, key: StorageKey) -> str | None: ...

    @abc.abstractmethod
    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None: ...

    @abc.abstractmethod
    async def get_data(self, key: StorageKey) -> dict[str, Any]: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    async def update_data(self, key: StorageKey, data: Mapping[str, Any]) -> dict[str, Any]:
        current = await self.get_data(key)
        current.update(data)
        await self.set_data(key, current)
        return current.copy()
