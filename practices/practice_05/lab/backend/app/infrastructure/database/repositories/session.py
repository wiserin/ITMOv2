from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.domain.entities.session import SessionEntity
from app.domain.exceptions.entities import NotFoundException
from app.infrastructure.database.models.session import SessionORM
from app.infrastructure.database.repositories.base import (
    SQLAlchemyRepositoryAdapter,
)


class SQLAlchemySessionRepositoryAdapter(SQLAlchemyRepositoryAdapter):
    async def create(self, entity: SessionEntity) -> SessionEntity:
        async with self._translate_errors():
            orm = self._to_orm(entity)
            self._session.add(orm)
            await self._session.flush()
            return self._from_orm(orm)

    async def _get_orm(
            self,
            session_id: UUID,
            *,
            for_update: bool = False) -> SessionORM:
        statement = (
            select(SessionORM).where(SessionORM.id == session_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            statement = statement.with_for_update()
        async with self._translate_errors():
            result = await self._session.scalars(statement)
            orm = result.one_or_none()
        if orm is None:
            raise NotFoundException(
                details={"entity": "session", "id": str(session_id)},
            )
        return orm

    async def get_by_id(
            self,
            session_id: UUID,
            *,
            for_update: bool = False) -> SessionEntity:
        orm = await self._get_orm(session_id, for_update=for_update)
        return self._from_orm(orm)

    async def list_by_user_id(
            self,
            user_id: UUID,
            *,
            limit: int,
            offset: int) -> tuple[SessionEntity, ...]:
        self._validate_pagination(limit, offset)
        statement = (
            select(SessionORM).where(SessionORM.user_id == user_id)
            .order_by(SessionORM.created_at, SessionORM.id)
            .limit(limit).offset(offset)
        )
        async with self._translate_errors():
            rows = (await self._session.scalars(statement)).all()
        return tuple(self._from_orm(orm) for orm in rows)

    async def update(self, entity: SessionEntity) -> SessionEntity:
        async with self._translate_errors():
            incoming = self._to_orm(entity)
            orm = await self._get_orm(incoming.id, for_update=True)
            self._assert_immutable(
                orm, incoming,
                ("user_id", "secret_hash", "created_at"),
                "session",
            )
            orm.last_used_at = incoming.last_used_at
            orm.expires_at = incoming.expires_at
            orm.closed_at = incoming.closed_at
            await self._session.flush()
            return self._from_orm(orm)

    async def delete(self, entity: SessionEntity) -> SessionEntity:
        async with self._translate_errors():
            incoming = self._to_orm(entity)
            orm = await self._get_orm(incoming.id, for_update=True)
            deleted = self._from_orm(orm)
            await self._session.delete(orm)
            await self._session.flush()
            return deleted

    @staticmethod
    def _to_orm(entity: SessionEntity) -> SessionORM:
        return SessionORM(
            id=entity.id,
            user_id=entity.user_id,
            secret_hash=entity.secret_hash,
            created_at=entity.created_at,
            last_used_at=entity.last_used_at,
            expires_at=entity.expires_at,
            closed_at=entity.closed_at,
        )

    @staticmethod
    def _from_orm(orm: SessionORM) -> SessionEntity:
        return SessionEntity(
            id=orm.id,
            user_id=orm.user_id,
            secret_hash=orm.secret_hash,
            created_at=orm.created_at,
            last_used_at=orm.last_used_at,
            expires_at=orm.expires_at,
            closed_at=orm.closed_at,
        )
