from collections.abc import AsyncIterator, Awaitable, Callable
from functools import partial
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import SessionController

Commit = Callable[[], Awaitable[None]]


async def get_auth_postgres_session() -> AsyncIterator[AsyncSession]:
    from app.infrastructure.database.factory import database_factory

    async with database_factory.session() as session:
        yield session


AuthPostgresSessionDI = Annotated[
    AsyncSession,
    Depends(get_auth_postgres_session, scope="function"),
]


def get_auth_commit(
        session: AuthPostgresSessionDI) -> Commit:
    return partial(SessionController.commit, session)


AuthCommitDI = Annotated[
    Commit, Depends(get_auth_commit),
]
