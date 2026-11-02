from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.entities.session import SessionEntity


class SessionRepository(Protocol):
    async def create(
            self,
            entity: SessionEntity) -> SessionEntity:
        ...

    async def get_by_id(
            self,
            session_id: UUID,
            *,
            for_update: bool = False) -> SessionEntity:
        ...

    async def list_by_user_id(
            self,
            user_id: UUID,
            *,
            limit: int,
            offset: int) -> tuple[SessionEntity, ...]: ...

    async def update(
            self,
            entity: SessionEntity) -> SessionEntity:
        ...

    async def delete(
            self,
            entity: SessionEntity) -> SessionEntity:
        ...
