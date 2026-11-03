from __future__ import annotations

import copy
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .base import BaseStorage, StateType, StorageKey, state_to_str


@dataclass
class _Record:
    data: dict[str, Any] = field(default_factory=dict)
    state: str | None = None


class MemoryStorage(BaseStorage):
    """Keeps everything in process memory. Great for development, lost on restart."""

    def __init__(self) -> None:
        self.storage: defaultdict[StorageKey, _Record] = defaultdict(_Record)

    async def close(self) -> None:
        self.storage.clear()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        self.storage[key].state = state_to_str(state)

    async def get_state(self, key: StorageKey) -> str | None:
        return self.storage[key].state if key in self.storage else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        self.storage[key].data = copy.deepcopy(dict(data))

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        return copy.deepcopy(self.storage[key].data) if key in self.storage else {}
