from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.domain.entities.credential import CredentialEntity
from app.domain.exceptions.entities import NotFoundException
from app.infrastructure.database.models.credential import (
    CredentialORM,
)
from app.infrastructure.database.repositories.base import (
    SQLAlchemyRepositoryAdapter,
)


class SQLAlchemyCredentialRepositoryAdapter(
        SQLAlchemyRepositoryAdapter):
    async def create(
            self,
            entity: CredentialEntity) -> CredentialEntity:
        async with self._translate_errors():
            orm = self._to_orm(entity)
            self._session.add(orm)
            await self._session.flush()
            return self._from_orm(orm)


    async def _get_orm(
            self,
            credential_id: UUID,
            *,
            for_update: bool = False) -> CredentialORM:
        statement = (
            select(CredentialORM)
            .where(CredentialORM.id == credential_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update()

        async with self._translate_errors():
            result = await self._session.scalars(statement)
            orm = result.one_or_none()

        if orm is None:
            raise NotFoundException(
                details={
                    "entity": "credential", "id": str(credential_id),
                },
            )
        return orm


    async def get_by_id(
            self,
            credential_id: UUID,
            *,
            for_update: bool = False) -> CredentialEntity:
        orm = await self._get_orm(
            credential_id, for_update=for_update,
        )
        return self._from_orm(orm)


    async def get_current_by_user_id(
            self,
            user_id: UUID,
            *,
            for_update: bool = False) -> CredentialEntity:
        statement = (
            select(CredentialORM)
            .where(
                CredentialORM.user_id == user_id,
                CredentialORM.is_current.is_(True),
            )
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update()
        async with self._translate_errors():
            result = await self._session.scalars(statement)
            orm = result.one_or_none()
        if orm is None:
            raise NotFoundException(details={
                "entity": "credential",
                "user_id": str(user_id),
                "is_current": True,
            })
        return self._from_orm(orm)


    async def list_by_user_id(
            self,
            user_id: UUID,
            *,
            limit: int,
            offset: int) -> tuple[CredentialEntity, ...]:
        self._validate_pagination(limit, offset)
        statement = (
            select(CredentialORM)
            .where(CredentialORM.user_id == user_id)
            .order_by(CredentialORM.created_at, CredentialORM.id)
            .limit(limit).offset(offset)
        )
        async with self._translate_errors():
            rows = (await self._session.scalars(statement)).all()
        return tuple(self._from_orm(orm) for orm in rows)

    async def update(
            self,
            entity: CredentialEntity) -> CredentialEntity:
        async with self._translate_errors():
            incoming = self._to_orm(entity)
            orm = await self._get_orm(incoming.id, for_update=True)
            self._assert_immutable(
                orm, incoming,
                ("user_id", "password_hash", "created_at"),
                "credential",
            )
            orm.is_current = incoming.is_current
            await self._session.flush()
            return self._from_orm(orm)

    async def delete(
            self,
            entity: CredentialEntity) -> CredentialEntity:
        async with self._translate_errors():
            incoming = self._to_orm(entity)
            orm = await self._get_orm(incoming.id, for_update=True)
            deleted = self._from_orm(orm)
            await self._session.delete(orm)
            await self._session.flush()
            return deleted

    @staticmethod
    def _to_orm(entity: CredentialEntity) -> CredentialORM:
        return CredentialORM(
            id=entity.id,
            user_id=entity.user_id,
            password_hash=entity.password_hash,
            is_current=entity.is_current,
            created_at=entity.created_at,
        )

    @staticmethod
    def _from_orm(orm: CredentialORM) -> CredentialEntity:
        return CredentialEntity(
            id=orm.id,
            user_id=orm.user_id,
            password_hash=orm.password_hash,
            is_current=orm.is_current,
            created_at=orm.created_at,
        )
