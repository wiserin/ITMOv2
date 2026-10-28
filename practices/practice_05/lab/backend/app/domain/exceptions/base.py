from __future__ import annotations


class BaseDomainException(Exception):
    default_message = "Domain operation failed"

    def __init__(
            self,
            message: str | None = None,
            *,
            details: dict[str, object] | None = None) -> None:
        self.message = self.default_message if message is None else message
        self.details = dict(details) if details is not None else {}
        super().__init__(self.message)
