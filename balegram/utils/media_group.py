from __future__ import annotations

from typing import Any

from ..methods.media_group import (
    AnyInputMedia,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)
from ..types.input_file import InputFile

MIN_ITEMS = 2
MAX_ITEMS = 10


class MediaGroupBuilder:
    """Collects the items of an album for :meth:`Bot.send_media_group`.

    >>> album = MediaGroupBuilder(caption="Holiday")
    >>> album.add_photo(FSInputFile("a.jpg")).add_photo("existing_file_id")
    >>> await bot.send_media_group(chat_id, album.build())
    """

    def __init__(self, caption: str | None = None) -> None:
        self.caption = caption
        self._items: list[AnyInputMedia] = []

    def __len__(self) -> int:
        return len(self._items)

    def _add(self, item: AnyInputMedia) -> MediaGroupBuilder:
        if len(self._items) >= MAX_ITEMS:
            raise ValueError(f"An album holds at most {MAX_ITEMS} items")
        self._items.append(item)
        return self

    def add_photo(
        self, media: InputFile | str, caption: str | None = None, **kwargs: Any
    ) -> MediaGroupBuilder:
        return self._add(InputMediaPhoto(media=media, caption=caption, **kwargs))

    def add_video(
        self, media: InputFile | str, caption: str | None = None, **kwargs: Any
    ) -> MediaGroupBuilder:
        return self._add(InputMediaVideo(media=media, caption=caption, **kwargs))

    def add_animation(
        self, media: InputFile | str, caption: str | None = None, **kwargs: Any
    ) -> MediaGroupBuilder:
        return self._add(InputMediaAnimation(media=media, caption=caption, **kwargs))

    def add_audio(
        self, media: InputFile | str, caption: str | None = None, **kwargs: Any
    ) -> MediaGroupBuilder:
        return self._add(InputMediaAudio(media=media, caption=caption, **kwargs))

    def add_document(
        self, media: InputFile | str, caption: str | None = None, **kwargs: Any
    ) -> MediaGroupBuilder:
        return self._add(InputMediaDocument(media=media, caption=caption, **kwargs))

    def build(self) -> list[AnyInputMedia]:
        if len(self._items) < MIN_ITEMS:
            raise ValueError(f"An album needs at least {MIN_ITEMS} items")
        items = [item.model_copy() for item in self._items]
        if self.caption and not items[0].caption:
            items[0].caption = self.caption
        return items
