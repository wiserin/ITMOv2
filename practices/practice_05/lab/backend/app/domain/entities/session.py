from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID, uuid4

from app.domain.exceptions.entities import (
    AuthenticationException,
    DataFormatException,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionEntity:
    user_id: UUID
    secret: str = field(repr=False)
    secret_hash: str = field(repr=False)
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)
    closed_at: datetime | None = None

    def ensure_usable(self, *, now: datetime | None = None) -> None:
        now = now if now is not None else datetime.now(UTC)
        if self.closed_at is not None:
            raise AuthenticationException(
                details={"reason": "session_closed"},
            )
        if now >= self.expires_at:
            raise AuthenticationException(
                details={"reason": "session_expired"},
            )

    def use(
            self,
            *,
            idle_timeout: timedelta,
            now: datetime | None = None) -> Self:
        now = now if now is not None else datetime.now(UTC)
        self.ensure_usable(now=now)
        if idle_timeout <= timedelta(0):
            raise DataFormatException(
                details={"field": "session_idle_timeout"},
            )
        last_used_at = max(now, self.last_used_at)
        return replace(
            self,
            last_used_at=last_used_at,
            expires_at=last_used_at + idle_timeout,
        )
