from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.login import LoginUseCase
from app.presentation.api.di.ports.jwt import JwtProviderDI
from app.presentation.api.di.ports.secret import SecretManagerDI
from app.presentation.api.di.ports.session_timeout import (
    SessionIdleTimeoutDI,
)
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
        session_repository: SessionRepositoryDI,
        jwt_provider: JwtProviderDI,
        secret_manager: SecretManagerDI,
        idle_timeout: SessionIdleTimeoutDI) -> LoginUseCase:
    return LoginUseCase(
        user_repository=user_repository,
        credential_repository=credential_repository,
        session_repository=session_repository,
        jwt_provider=jwt_provider,
        secret_manager=secret_manager,
        session_idle_timeout_minutes=idle_timeout,
    )

LoginUseCaseDI = Annotated[
    LoginUseCase,
    Depends(get_login_usecase),
]
