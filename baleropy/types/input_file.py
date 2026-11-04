from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path

DEFAULT_FILENAME = "file"


class InputFile(ABC):
    """A file uploaded with ``multipart/form-data``."""

    def __init__(self, filename: str | None = None) -> None:
        self.filename = filename or DEFAULT_FILENAME

    @abstractmethod
    async def read(self) -> bytes: ...


class BufferedInputFile(InputFile):
    def __init__(self, data: bytes, filename: str = DEFAULT_FILENAME) -> None:
        super().__init__(filename)
        self.data = data

    async def read(self) -> bytes:
        return self.data

    @classmethod
    def from_file(cls, path: str | Path, filename: str | None = None) -> BufferedInputFile:
        path = Path(path)
        return cls(path.read_bytes(), filename or path.name)


class FSInputFile(InputFile):
    """Lazily reads a file from disk when the request is sent."""

    def __init__(self, path: str | Path, filename: str | None = None) -> None:
        path = Path(path)
        super().__init__(filename or path.name)
        self.path = path

    async def read(self) -> bytes:
        return await asyncio.to_thread(self.path.read_bytes)
