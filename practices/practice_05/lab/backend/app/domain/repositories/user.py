from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.entities.user import UserEntity


class UserRepository(Protocol):
    async def create(self, entity: UserEntity) -> UserEntity: ...

    async def get_by_id(
            self,
            user_id: UUID,
            *,
            for_update: bool = False) -> UserEntity:
        ...

    async def get_by_email(
            self,
            email: str,
            *,
            for_update: bool = False) -> UserEntity:
        ...

    async def find_by_username_prefix(
            self,
            username_prefix: str,
            *,
            limit: int,
            offset: int) -> tuple[UserEntity, ...]:
        """Return prefix matches ordered by username and ID."""
        ...

    async def update(self, entity: UserEntity) -> UserEntity: ...

    async def delete(self, entity: UserEntity) -> UserEntity: ...
