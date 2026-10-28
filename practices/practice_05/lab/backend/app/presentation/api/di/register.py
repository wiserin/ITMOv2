from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.register import RegisterUseCase
from app.presentation.api.di.repositories.credential import (
    CredentialRepositoryDI,
)
from app.presentation.api.di.repositories.user import UserRepositoryDI


def get_register_usecase(
        user_repository: UserRepositoryDI,
        credentials: CredentialRepositoryDI) -> RegisterUseCase:
    return RegisterUseCase(
        user_repository=user_repository,
        credential_repository=credentials,
    )


RegisterUseCaseDI = Annotated[
    RegisterUseCase,
    Depends(get_register_usecase),
]
