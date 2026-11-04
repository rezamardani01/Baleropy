from __future__ import annotations

from .base import BoundObject


class PhotoSize(BoundObject):
    file_id: str
    file_unique_id: str
    width: int
    height: int
    file_size: int | None = None


class _FileBase(BoundObject):
    file_id: str
    file_unique_id: str


class Animation(_FileBase):
    width: int
    height: int
    duration: int
    thumbnail: PhotoSize | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None


class Audio(_FileBase):
    duration: int
    title: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None


class Document(_FileBase):
    thumbnail: PhotoSize | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None


class Video(_FileBase):
    width: int
    height: int
    duration: int
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None


class Voice(_FileBase):
    duration: int | None = None
    mime_type: str | None = None
    file_size: int | None = None


class Sticker(_FileBase):
    type: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None


class StickerSet(BoundObject):
    name: str
    title: str
    stickers: list[Sticker] = []
    thumbnail: PhotoSize | None = None


class File(BoundObject):
    file_id: str
    file_unique_id: str
    file_size: int | None = None
    file_path: str | None = None


class Contact(BoundObject):
    phone_number: str
    first_name: str
    last_name: str | None = None
    user_id: int | None = None


class Location(BoundObject):
    longitude: float
    latitude: float


__all__ = [
    "Animation",
    "Audio",
    "Contact",
    "Document",
    "File",
    "Location",
    "PhotoSize",
    "Sticker",
    "StickerSet",
    "Video",
    "Voice",
]
