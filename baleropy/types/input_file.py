from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

DEFAULT_FILENAME = "file"


class InputFile(ABC):
    """A file uploaded with ``multipart/form-data``."""

    def __init__(self, filename: str | None = None) -> None:
        self.filename = filename or DEFAULT_FILENAME

    @abstractmethod
    async def read(self) -> bytes: ...

    async def chunks(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        """Read the file in chunks. Buffered files return their data as a single chunk."""
        yield await self.read()


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
    """Streams a file from disk when the request is sent."""

    def __init__(self, path: str | Path, filename: str | None = None) -> None:
        path = Path(path)
        super().__init__(filename or path.name)
        self.path = path

    async def read(self) -> bytes:
        return await asyncio.to_thread(self.path.read_bytes)

    async def chunks(self, chunk_size: int = 65536) -> AsyncIterator[bytes]:
        with self.path.open("rb") as file:
            while chunk := await asyncio.to_thread(file.read, chunk_size):
                yield chunk
