from __future__ import annotations

from typing import Any


class BalegramError(Exception):
    """Base class for every error raised by balegram."""


class DetailedError(BalegramError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message


class BaleAPIError(DetailedError):
    """The Bale server answered with ``ok: false``."""

    def __init__(
        self,
        method: str,
        message: str,
        error_code: int | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.method = method
        self.error_code = error_code
        self.parameters = parameters or {}

    def __str__(self) -> str:
        return f"Bale server says [{self.error_code}] {self.message} (method: {self.method})"


class BaleBadRequest(BaleAPIError):
    """HTTP 400."""


class BaleUnauthorized(BaleAPIError):
    """HTTP 401 - the token is invalid."""


class BaleForbidden(BaleAPIError):
    """HTTP 403."""


class BaleNotFound(BaleAPIError):
    """HTTP 404."""


class BaleRetryAfter(BaleAPIError):
    """HTTP 429 - slow down for ``retry_after`` seconds."""

    @property
    def retry_after(self) -> int:
        return int(self.parameters.get("retry_after", 0))


class BaleServerError(BaleAPIError):
    """HTTP 5xx."""


class BaleNetworkError(DetailedError):
    """Connection problem or timeout while talking to Bale."""


class ClientDecodeError(DetailedError):
    """The response body could not be decoded or validated."""

    def __init__(self, message: str, original: Exception, data: Any) -> None:
        super().__init__(message)
        self.original = original
        self.data = data


class SkipHandler(BalegramError):
    """Raise inside a handler to let the next matching handler run."""


class CancelHandler(BalegramError):
    """Raise inside a middleware to stop processing the event."""


class UnhandledEvent(BalegramError):
    """Internal marker: no handler took the event."""
