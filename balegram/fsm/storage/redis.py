from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .base import BaseStorage, StateType, StorageKey, state_to_str


class RedisStorage(BaseStorage):
    """Persistent FSM storage on Redis (``pip install balegram[redis]``).

    ``state_ttl`` / ``data_ttl`` are expiry times in seconds (``None`` keeps keys forever).
    """

    def __init__(
        self,
        redis: Any,
        prefix: str = "balegram_fsm",
        state_ttl: int | None = None,
        data_ttl: int | None = None,
    ) -> None:
        self.redis = redis
        self.prefix = prefix
        self.state_ttl = state_ttl
        self.data_ttl = data_ttl

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> RedisStorage:
        try:
            from redis.asyncio import Redis
        except ImportError as error:  # pragma: no cover
            raise ImportError("Install the extra: pip install 'balegram[redis]'") from error
        return cls(Redis.from_url(url), **kwargs)

    def _key(self, key: StorageKey, part: str) -> str:
        return f"{self.prefix}:{key.bot_id}:{key.chat_id}:{key.user_id}:{part}"

    async def close(self) -> None:
        await self.redis.aclose()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        redis_key = self._key(key, "state")
        value = state_to_str(state)
        if value is None:
            await self.redis.delete(redis_key)
        else:
            await self.redis.set(redis_key, value, ex=self.state_ttl)

    async def get_state(self, key: StorageKey) -> str | None:
        value = await self.redis.get(self._key(key, "state"))
        if isinstance(value, bytes):
            return value.decode()
        return value  # type: ignore[no-any-return]

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        redis_key = self._key(key, "data")
        if not data:
            await self.redis.delete(redis_key)
        else:
            await self.redis.set(redis_key, json.dumps(dict(data)), ex=self.data_ttl)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        value = await self.redis.get(self._key(key, "data"))
        if value is None:
            return {}
        loaded: dict[str, Any] = json.loads(value)
        return loaded
