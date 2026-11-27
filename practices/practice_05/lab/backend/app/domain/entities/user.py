from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums.user_role import UserRole


@dataclass(frozen=True, slots=True, kw_only=True)
class UserEntity:
    email: str
    username: str
    created_at: datetime
    updated_at: datetime
    id: UUID = field(default_factory=uuid4)
    role: UserRole = UserRole.USER
    is_active: bool = True
    display_name: str | None = None
