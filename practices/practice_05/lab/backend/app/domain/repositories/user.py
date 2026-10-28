from __future__ import annotations

from typing import Protocol

from app.domain.entities.user import UserEntity


class UserRepository(Protocol):
    async def find_by_username_prefix(
            self,
            username_prefix: str,
            *,
            limit: int,
            offset: int) -> tuple[UserEntity, ...]:
        """Return a page of literal username-prefix matches ordered by username and ID."""
        ...
