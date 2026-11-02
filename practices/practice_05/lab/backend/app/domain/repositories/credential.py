from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.entities.credential import CredentialEntity


class CredentialRepository(Protocol):
    async def create(
            self,
            entity: CredentialEntity) -> CredentialEntity:
        ...

    async def get_by_id(
            self,
            credential_id: UUID,
            *,
            for_update: bool = False) -> CredentialEntity:
        ...

    async def get_current_by_user_id(
            self,
            user_id: UUID,
            *,
            for_update: bool = False) -> CredentialEntity:
        ...

    async def list_by_user_id(
            self,
            user_id: UUID,
            *,
            limit: int,
            offset: int) -> tuple[CredentialEntity, ...]: ...

    async def update(
            self,
            entity: CredentialEntity) -> CredentialEntity:
        ...

    async def delete(
            self,
            entity: CredentialEntity) -> CredentialEntity:
        ...
