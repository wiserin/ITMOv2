from typing import Annotated

from fastapi import Depends

from app.domain.repositories.user import UserRepository
from app.infrastructure.database.repositories.user import (
    SQLAlchemyUserRepositoryAdapter,
)
from app.presentation.api.di.clients.auth_postgres import (
    AuthPostgresSessionDI,
)
from app.presentation.api.di.clients.postgres import PostgresSessionDI


def get_user_repository(session: PostgresSessionDI) -> UserRepository:
    return SQLAlchemyUserRepositoryAdapter(session=session)


UserRepositoryDI = Annotated[
    UserRepository, Depends(get_user_repository),
]


def get_auth_user_repository(
        session: AuthPostgresSessionDI) -> UserRepository:
    return SQLAlchemyUserRepositoryAdapter(session=session)


AuthUserRepositoryDI = Annotated[
    UserRepository, Depends(get_auth_user_repository),
]
