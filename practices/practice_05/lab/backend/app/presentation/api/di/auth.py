from __future__ import annotations

from app.application.usecases.auth import AuthUseCase
from app.presentation.api.di.clients.auth_postgres import AuthCommitDI
from app.presentation.api.di.ports.jwt import JwtProviderDI
from app.presentation.api.di.ports.secret import SecretManagerDI
from app.presentation.api.di.ports.session_timeout import (
    SessionIdleTimeoutDI,
)
from app.presentation.api.di.repositories.session import (
    AuthSessionRepositoryDI,
)
from app.presentation.api.di.repositories.user import (
    AuthUserRepositoryDI,
)


def get_auth_usecase(
        user_repository: AuthUserRepositoryDI,
        session_repository: AuthSessionRepositoryDI,
        jwt_provider: JwtProviderDI,
        secret_manager: SecretManagerDI,
        idle_timeout: SessionIdleTimeoutDI,
        commit: AuthCommitDI) -> AuthUseCase:
    return AuthUseCase(
        user_repository=user_repository,
        session_repository=session_repository,
        jwt_provider=jwt_provider,
        secret_manager=secret_manager,
        session_idle_timeout_minutes=idle_timeout,
        commit=commit,
    )
