from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


async def get_postgres_session() -> AsyncIterator[AsyncSession]:
    from app.infrastructure.database.factory import database_factory

    async with database_factory.session() as session:
        yield session


PostgresSessionDI = Annotated[
    AsyncSession,
    Depends(get_postgres_session, scope="function"),
]
