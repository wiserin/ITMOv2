from typing import Annotated

from fastapi import Depends

from app.application.usecases.logout import LogoutUseCase
from app.presentation.api.di.ports.jwt import JwtProviderDI
from app.presentation.api.di.ports.secret import SecretManagerDI
from app.presentation.api.di.repositories.session import (
    SessionRepositoryDI,
)
from app.presentation.api.di.repositories.user import UserRepositoryDI


def get_logout_usecase(
        user_repository: UserRepositoryDI,
        session_repository: SessionRepositoryDI,
        jwt_provider: JwtProviderDI,
        secret_manager: SecretManagerDI) -> LogoutUseCase:
    return LogoutUseCase(
        user_repository=user_repository,
        session_repository=session_repository,
        jwt_provider=jwt_provider,
        secret_manager=secret_manager,
    )


LogoutUseCaseDI = Annotated[
    LogoutUseCase, Depends(get_logout_usecase),
]
