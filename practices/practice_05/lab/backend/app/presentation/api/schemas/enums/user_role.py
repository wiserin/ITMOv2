from __future__ import annotations

from enum import StrEnum
from typing import Self

from app.domain.enums.user_role import UserRole
from app.domain.exceptions.entities import DataFormatException


class UserRoleResponse(StrEnum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

    @classmethod
    def from_domain(cls, role: UserRole) -> Self:
        try:
            return cls(UserRole(role).to_string())
        except ValueError as exc:
            raise DataFormatException(details={"field": "role", "value": role}) from exc
