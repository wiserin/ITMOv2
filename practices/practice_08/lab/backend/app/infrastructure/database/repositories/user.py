from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.domain.entities.user import UserEntity
from app.domain.enums.user_role import UserRole
from app.domain.exceptions.entities import (
    DataFormatException,
    NotFoundException,
)
from app.infrastructure.database.models.user import UserORM
from app.infrastructure.database.repositories.base import (
    SQLAlchemyRepositoryAdapter,
)


class SQLAlchemyUserRepositoryAdapter(SQLAlchemyRepositoryAdapter):
    async def create(self, entity: UserEntity) -> UserEntity:
        async with self._translate_errors():
            orm = self._to_orm(entity)
            self._session.add(orm)
            await self._session.flush()
            return self._from_orm(orm)

    async def _get_orm(
            self,
            user_id: UUID,
            *,
            for_update: bool = False) -> UserORM:
        statement = (
            select(UserORM)
            .where(UserORM.id == user_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update()
        async with self._translate_errors():
            result = await self._session.scalars(statement)
            orm = result.one_or_none()
        if orm is None:
            raise NotFoundException(
                details={"entity": "user", "id": str(user_id)},
            )
        return orm

    async def get_by_id(
            self,
            user_id: UUID,
            *,
            for_update: bool = False) -> UserEntity:
        orm = await self._get_orm(user_id, for_update=for_update)
        return self._from_orm(orm)

    async def get_by_email(
            self,
            email: str,
            *,
            for_update: bool = False) -> UserEntity:
        statement = (
            select(UserORM)
            .where(UserORM.email == email)
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update()
        async with self._translate_errors():
            result = await self._session.scalars(statement)
            orm = result.one_or_none()
        if orm is None:
            raise NotFoundException(details={
                "entity": "user", "field": "email", "value": email,
            })
        return self._from_orm(orm)

    async def find_by_username_prefix(
            self,
            username_prefix: str,
            *,
            limit: int,
            offset: int) -> tuple[UserEntity, ...]:
        self._validate_pagination(limit, offset)
        statement = (
            select(UserORM)
            .where(UserORM.username.startswith(
                username_prefix, autoescape=True,
            ))
            .order_by(UserORM.username, UserORM.id)
            .limit(limit).offset(offset)
        )
        async with self._translate_errors():
            rows = (await self._session.scalars(statement)).all()
        return tuple(self._from_orm(orm) for orm in rows)

    async def update(self, entity: UserEntity) -> UserEntity:
        async with self._translate_errors():
            incoming = self._to_orm(entity)
            orm = await self._get_orm(incoming.id, for_update=True)
            self._assert_immutable(
                orm, incoming, ("created_at",), "user",
            )
            orm.email = incoming.email
            orm.username = incoming.username
            orm.display_name = incoming.display_name
            orm.role = incoming.role
            orm.is_active = incoming.is_active
            orm.updated_at = incoming.updated_at
            # Persist the domain timestamp; skip ORM onupdate SQL.
            flag_modified(orm, "updated_at")
            await self._session.flush()
            return self._from_orm(orm)

    async def delete(self, entity: UserEntity) -> UserEntity:
        async with self._translate_errors():
            incoming = self._to_orm(entity)
            orm = await self._get_orm(incoming.id, for_update=True)
            deleted = self._from_orm(orm)
            await self._session.delete(orm)
            await self._session.flush()
            return deleted

    @staticmethod
    def _to_orm(entity: UserEntity) -> UserORM:
        return UserORM(
            id=entity.id,
            email=entity.email,
            username=entity.username,
            display_name=entity.display_name,
            role=int(entity.role),
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @staticmethod
    def _from_orm(orm: UserORM) -> UserEntity:
        try:
            role = UserRole(orm.role)
        except ValueError as exc:
            raise DataFormatException(details={
                "entity": "user", "field": "role", "value": orm.role,
            }) from exc
        return UserEntity(
            id=orm.id,
            email=orm.email,
            username=orm.username,
            display_name=orm.display_name,
            role=role,
            is_active=orm.is_active,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
