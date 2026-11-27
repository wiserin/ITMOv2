from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.register import RegisterUseCase
from app.presentation.api.di.ports.secret import SecretManagerDI
from app.presentation.api.di.repositories.credential import (
    CredentialRepositoryDI,
)
from app.presentation.api.di.repositories.user import UserRepositoryDI


def get_register_usecase(
        user_repository: UserRepositoryDI,
        credentials: CredentialRepositoryDI,
        secret_manager: SecretManagerDI) -> RegisterUseCase:
    return RegisterUseCase(
        user_repository=user_repository,
        credential_repository=credentials,
        secret_manager=secret_manager,
    )


RegisterUseCaseDI = Annotated[
    RegisterUseCase,
    Depends(get_register_usecase),
]
