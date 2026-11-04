from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel, ValidationError

from ..types import CallbackQuery
from .base import Filter, FilterResult
from .magic import MagicFilter

T = TypeVar("T", bound="CallbackData")

MAX_CALLBACK_BYTES = 64


class CallbackData(BaseModel):
    """Typed ``callback_data`` factory.

    >>> class Item(CallbackData, prefix="item"):
    ...     id: int
    ...     action: str
    >>> Item(id=5, action="buy").pack()
    'item:5:buy'
    """

    __prefix__: ClassVar[str]
    __sep__: ClassVar[str]

    def __init_subclass__(cls, *, prefix: str, sep: str = ":", **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if sep in prefix:
            raise ValueError(f"Separator {sep!r} must not be part of the prefix {prefix!r}")
        cls.__prefix__ = prefix
        cls.__sep__ = sep

    def _encode(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(int(value))
        if isinstance(value, Enum):
            value = value.value
        text = str(value)
        if self.__sep__ in text:
            raise ValueError(f"Value {text!r} contains the separator {self.__sep__!r}")
        return text

    def pack(self) -> str:
        parts = [self.__prefix__, *(self._encode(v) for v in self.model_dump().values())]
        packed = self.__sep__.join(parts)
        if len(packed.encode()) > MAX_CALLBACK_BYTES:
            raise ValueError(
                f"callback_data is {len(packed.encode())} bytes, Bale allows {MAX_CALLBACK_BYTES}"
            )
        return packed

    @classmethod
    def unpack(cls: type[T], value: str) -> T:
        prefix, *parts = value.split(cls.__sep__)
        if prefix != cls.__prefix__:
            raise ValueError(f"Bad prefix ({prefix!r} != {cls.__prefix__!r})")
        names = list(cls.model_fields)
        if len(parts) != len(names):
            raise ValueError(f"Expected {len(names)} fields, got {len(parts)}")
        values = {
            name: (part if part != "" else None) for name, part in zip(names, parts, strict=True)
        }
        return cls.model_validate(values)

    @classmethod
    def filter(cls: type[T], rule: MagicFilter | None = None) -> CallbackQueryFilter:
        return CallbackQueryFilter(cls, rule)


class CallbackQueryFilter(Filter):
    def __init__(self, callback_data: type[CallbackData], rule: MagicFilter | None = None) -> None:
        self.callback_data = callback_data
        self.rule = rule

    async def __call__(self, event: Any, **data: Any) -> FilterResult:
        if not isinstance(event, CallbackQuery) or not event.data:
            return False
        if not event.data.startswith(self.callback_data.__prefix__ + self.callback_data.__sep__):
            return False
        try:
            parsed = self.callback_data.unpack(event.data)
        except (ValueError, ValidationError):
            return False
        if self.rule is not None and not self.rule.resolve(parsed):
            return False
        return {"callback_data": parsed}
