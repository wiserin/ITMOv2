from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions.entities import (
    ConflictException,
    DataFormatException,
)
from app.infrastructure.database.errors import (
    translate_database_error,
)
from app.infrastructure.database.models.general import Base


class SQLAlchemyRepositoryAdapter:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session


    @asynccontextmanager
    async def _translate_errors(self) -> AsyncGenerator[None]:
        try:
            yield
        except DBAPIError as exc:
            raise translate_database_error(exc) from exc


    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        if limit < 1 or offset < 0:
            raise DataFormatException(
                details={"limit": limit, "offset": offset},
            )


    @staticmethod
    def _assert_immutable(
            current: Base,
            incoming: Base,
            fields: tuple[str, ...],
            entity: str) -> None:
        changed = [
            name for name in fields
            if getattr(current, name) != getattr(incoming, name)
        ]
        if changed:
            raise ConflictException(details={
                "entity": entity,
                "reason": "immutable_fields",
                "fields": changed,
            })
