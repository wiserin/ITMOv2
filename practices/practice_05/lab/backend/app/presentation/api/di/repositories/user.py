from typing import Annotated

from fastapi import Depends

from app.domain.repositories.user import UserRepository
from app.infrastructure.database.repositories.user import (
    SQLAlchemyUserRepositoryAdapter,
)
from app.presentation.api.di.clients.postgres import PostgresSessionDI


def get_user_repository(session: PostgresSessionDI) -> UserRepository:
    return SQLAlchemyUserRepositoryAdapter(session=session)


UserRepositoryDI = Annotated[
    UserRepository, Depends(get_user_repository),
]
