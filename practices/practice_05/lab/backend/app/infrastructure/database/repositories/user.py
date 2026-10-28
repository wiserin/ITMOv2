from __future__ import annotations

from app.domain.entities.user import UserEntity
from app.domain.exceptions.entities import NotImplementedException


class UnconfiguredUserRepositoryAdapter:
    async def find_by_username_prefix(
            self,
            username_prefix: str,
            *,
            limit: int,
            offset: int) -> tuple[UserEntity, ...]:
        raise NotImplementedException(details={
            "entity": "user", "operation": "find_by_username_prefix",
        })
