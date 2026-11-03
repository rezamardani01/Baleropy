from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiServer:
    """Describes where the Bale Bot API lives. Subclass or build your own for proxies/mirrors."""

    base: str = "https://tapi.bale.ai/bot{token}/{method}"
    file: str = "https://tapi.bale.ai/file/bot{token}/{path}"

    def api_url(self, token: str, method: str) -> str:
        return self.base.format(token=token, method=method)

    def file_url(self, token: str, path: str) -> str:
        return self.file.format(token=token, path=path)

    @classmethod
    def from_base(cls, base: str) -> ApiServer:
        base = base.rstrip("/")
        return cls(
            base=f"{base}/bot{{token}}/{{method}}",
            file=f"{base}/file/bot{{token}}/{{path}}",
        )


PRODUCTION = ApiServer()
BUSINESS = ApiServer(
    base="https://tapi.bale.ai/business/bot{token}/{method}",
    file=PRODUCTION.file,
)
