from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


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
