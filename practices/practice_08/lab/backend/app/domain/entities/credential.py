from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class CredentialEntity:
    user_id: UUID
    password_hash: str = field(repr=False)
    created_at: datetime
    id: UUID = field(default_factory=uuid4)
    is_current: bool = True
