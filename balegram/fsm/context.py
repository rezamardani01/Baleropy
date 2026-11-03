from __future__ import annotations

from typing import Any

from .storage.base import BaseStorage, StateType, StorageKey


class FSMContext:
    """Per-user (or per-chat) view of the storage, injected into handlers as ``state``."""

    def __init__(self, storage: BaseStorage, key: StorageKey) -> None:
        self.storage = storage
        self.key = key

    async def set_state(self, state: StateType = None) -> None:
        await self.storage.set_state(self.key, state)

    async def get_state(self) -> str | None:
        return await self.storage.get_state(self.key)

    async def set_data(self, data: dict[str, Any]) -> None:
        await self.storage.set_data(self.key, data)

    async def get_data(self) -> dict[str, Any]:
        return await self.storage.get_data(self.key)

    async def update_data(
        self, data: dict[str, Any] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        if data:
            kwargs.update(data)
        return await self.storage.update_data(self.key, kwargs)

    async def get_value(self, key: str, default: Any = None) -> Any:
        return (await self.get_data()).get(key, default)

    async def clear(self) -> None:
        await self.set_state(None)
        await self.set_data({})
