from __future__ import annotations

from app.application.usecases.auth import AuthUseCase
from app.presentation.api.di.repositories.session import (
    SessionRepositoryDI,
)
from app.presentation.api.di.repositories.user import UserRepositoryDI


def get_auth_usecase(
        user_repository: UserRepositoryDI,
        session_repository: SessionRepositoryDI) -> AuthUseCase:
    return AuthUseCase(
        user_repository=user_repository,
        session_repository=session_repository,
    )
