"""Length limits documented by Bale, enforced before a request is sent."""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, Field

#: sendMessage / editMessageText
Text = Annotated[str, Field(min_length=1, max_length=4096)]
#: captions of sendPhoto, sendDocument... and editMessageCaption
Caption = Annotated[str, Field(max_length=4096)]
#: caption of an InputMedia item (sendMediaGroup)
MediaCaption = Annotated[str, Field(max_length=1024)]
#: answerCallbackQuery text
CallbackText = Annotated[str, Field(max_length=200)]
#: sticker set name and title
StickerName = Annotated[str, Field(min_length=1, max_length=64)]


def _max_bytes(limit: int) -> AfterValidator:
    def check(value: str) -> str:
        if len(value.encode()) > limit:
            raise ValueError(f"must be at most {limit} bytes (UTF-8)")
        return value

    return AfterValidator(check)


InvoiceTitle = Annotated[str, Field(min_length=1, max_length=32)]
InvoiceDescription = Annotated[str, Field(min_length=1, max_length=255)]
InvoicePayload = Annotated[str, Field(min_length=1), _max_bytes(128)]
