from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from ..client.bot import Bot


class BaleObject(BaseModel):
    """Base model of every Bale type. Unknown fields are kept, so API additions never break."""

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        use_enum_values=False,
        arbitrary_types_allowed=True,
        frozen=False,
    )


class BoundObject(BaleObject):
    """A Bale object that can remember the :class:`Bot` it was received through."""

    _bot: Bot | None = None

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            raise RuntimeError(f"{type(self).__name__} is not bound to a Bot instance")
        return self._bot

    def model_post_init(self, __context: Any) -> None:
        self._bot = None if __context is None else __context.get("bot")
