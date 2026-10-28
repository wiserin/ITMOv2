from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.login import LoginUseCase
from app.presentation.api.di.repositories.credential import (
    CredentialRepositoryDI,
)
from app.presentation.api.di.repositories.session import (
    SessionRepositoryDI,
)
from app.presentation.api.di.repositories.user import UserRepositoryDI


def get_login_usecase(
        user_repository: UserRepositoryDI,
        credential_repository: CredentialRepositoryDI,
        session_repository: SessionRepositoryDI) -> LoginUseCase:
    return LoginUseCase(
        user_repository=user_repository,
        credential_repository=credential_repository,
        session_repository=session_repository,
    )

LoginUseCaseDI = Annotated[
    LoginUseCase,
    Depends(get_login_usecase),
]
