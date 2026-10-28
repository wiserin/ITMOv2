from typing import Annotated

from fastapi import Depends

from app.domain.repositories.credential import CredentialRepository
from app.infrastructure.database.repositories.credential import (
    SQLAlchemyCredentialRepositoryAdapter,
)
from app.presentation.api.di.clients.postgres import PostgresSessionDI


def get_credential_repository(
        session: PostgresSessionDI) -> CredentialRepository:
    return SQLAlchemyCredentialRepositoryAdapter(session=session)


CredentialRepositoryDI = Annotated[
    CredentialRepository, Depends(get_credential_repository),
]
