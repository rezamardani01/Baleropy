from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, TypeAdapter

from ..exceptions import ClientDecodeError
from ..types.input_file import InputFile

if TYPE_CHECKING:
    from ..client.bot import Bot

T = TypeVar("T")


class BaleMethod(BaseModel, Generic[T]):
    """A typed description of one Bot API call."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True, populate_by_name=True)

    __api_method__: ClassVar[str]
    __returning__: ClassVar[Any]

    def build_request(self) -> tuple[dict[str, Any], dict[str, InputFile]]:
        """Split the method into plain fields and uploaded files."""
        raw = self.model_dump(by_alias=True, exclude_none=True)
        # Bale rejects an integer chat_id on some methods ("chat id is empty" on sendChatAction)
        # but accepts strings everywhere, so always send chat ids as strings.
        for key in ("chat_id", "from_chat_id"):
            if isinstance(raw.get(key), int):
                raw[key] = str(raw[key])
        data: dict[str, Any] = {}
        files: dict[str, InputFile] = {}
        for key, value in raw.items():
            if isinstance(value, InputFile):
                files[key] = value
            else:
                data[key] = _attach_nested(value, files)
        return data, files

    def build_response(self, result: Any, bot: Bot | None = None) -> T:
        try:
            adapter: TypeAdapter[T] = TypeAdapter(self.__returning__)
            return adapter.validate_python(result, context={"bot": bot})
        except Exception as error:
            raise ClientDecodeError(
                f"Failed to decode answer of {self.__api_method__}: {error}", error, result
            ) from error

    async def as_(self, bot: Bot) -> T:
        return await bot(self)


def _attach_nested(value: Any, files: dict[str, InputFile]) -> Any:
    """Replace InputFile objects nested in lists/dicts by ``attach://`` references."""
    if isinstance(value, InputFile):
        key = f"attached{len(files)}"
        files[key] = value
        return f"attach://{key}"
    if isinstance(value, list):
        return [_attach_nested(item, files) for item in value]
    if isinstance(value, dict):
        return {k: _attach_nested(v, files) for k, v in value.items()}
    return value
