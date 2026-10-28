from typing import Annotated

from fastapi import Depends

from app.domain.repositories.session import SessionRepository
from app.infrastructure.database.repositories.session import (
    SQLAlchemySessionRepositoryAdapter,
)
from app.presentation.api.di.clients.postgres import PostgresSessionDI


def get_session_repository(
        session: PostgresSessionDI) -> SessionRepository:
    return SQLAlchemySessionRepositoryAdapter(session=session)


SessionRepositoryDI = Annotated[
    SessionRepository, Depends(get_session_repository),
]
