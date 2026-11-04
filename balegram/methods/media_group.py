from __future__ import annotations

from typing import ClassVar, Literal

from ..types import Message
from ..types.base import BaleObject
from ..types.input_file import InputFile
from .base import BaleMethod
from .limits import MediaCaption


class InputMedia(BaleObject):
    model_config = BaleObject.model_config | {"arbitrary_types_allowed": True}

    media: InputFile | str
    caption: MediaCaption | None = None
    thumbnail: InputFile | str | None = None


class InputMediaPhoto(InputMedia):
    type: Literal["photo"] = "photo"


class InputMediaVideo(InputMedia):
    type: Literal["video"] = "video"
    width: int | None = None
    height: int | None = None
    duration: int | None = None


class InputMediaAnimation(InputMedia):
    type: Literal["animation"] = "animation"
    width: int | None = None
    height: int | None = None
    duration: int | None = None


class InputMediaAudio(InputMedia):
    type: Literal["audio"] = "audio"
    duration: int | None = None
    title: str | None = None


class InputMediaDocument(InputMedia):
    type: Literal["document"] = "document"


AnyInputMedia = (
    InputMediaPhoto | InputMediaVideo | InputMediaAnimation | InputMediaAudio | InputMediaDocument
)


class SendMediaGroup(BaleMethod[list[Message]]):
    __api_method__: ClassVar[str] = "sendMediaGroup"
    __returning__: ClassVar = list[Message]

    chat_id: int | str
    media: list[AnyInputMedia]
    reply_to_message_id: int | None = None
