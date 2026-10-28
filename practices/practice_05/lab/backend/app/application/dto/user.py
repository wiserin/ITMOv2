from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import UUID

from app.domain.entities.user import UserEntity
from app.domain.enums.user_role import UserRole


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDTO:
    id: UUID
    email: str
    username: str
    role: UserRole
    is_active: bool
    display_name: str | None = None

    @classmethod
    def from_entity(cls, entity: UserEntity) -> Self:
        return cls(
            id=entity.id, email=entity.email, username=entity.username,
            role=entity.role, is_active=entity.is_active, display_name=entity.display_name,
        )
