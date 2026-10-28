from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.dto.login import LoginDTO, LoginResultDTO
from app.application.usecases.base import BaseUseCase
from app.domain.entities.session import SessionEntity
from app.domain.entities.token import SessionTokenEntity
from app.domain.exceptions.entities import (
    AuthenticationException,
    NotFoundException,
)
from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.domain.repositories.credential import CredentialRepository
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


class LoginUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository,
            credential_repository: CredentialRepository,
            session_repository: SessionRepository,
            jwt_provider: JwtProviderPort,
            secret_manager: SecretManagerPort,
            session_idle_timeout_minutes: int) -> None:
        super().__init__()
        self._user_repository = user_repository
        self._credential_repository = credential_repository
        self._session_repository = session_repository
        self._jwt_provider = jwt_provider
        self._secret_manager = secret_manager
        self._idle_timeout = timedelta(
            minutes=session_idle_timeout_minutes,
        )

    async def login(self, data: LoginDTO) -> LoginResultDTO:
        credentials = self._credential_repository
        try:
            user = await self._user_repository.get_by_email(
                data.email.strip().lower(),
            )
            if not user.is_active:
                raise AuthenticationException(
                    details={"reason": "invalid_credentials"},
                )
            credential = (
                await credentials.get_current_by_user_id(
                    user.id,
                )
            )
            await self._secret_manager.verify_secret(
                data.password, credential.password_hash,
            )
            secret = self._secret_manager.generate_random_secret()
            secret_hash = await self._secret_manager.hash_secret(
                secret,
            )
            # Serialize with password changes and user deactivation.
            user = await self._user_repository.get_by_id(
                user.id, for_update=True,
            )
            current = (
                await credentials.get_current_by_user_id(
                    user.id, for_update=True,
                )
            )
            if not user.is_active or current.id != credential.id:
                raise AuthenticationException()
        except (NotFoundException, AuthenticationException) as exc:
            raise AuthenticationException(
                details={"reason": "invalid_credentials"},
            ) from exc
        now = datetime.now(UTC)
        session = SessionEntity(
            user_id=user.id,
            secret=secret,
            secret_hash=secret_hash,
            created_at=now,
            last_used_at=now,
            expires_at=now + self._idle_timeout,
        )
        await self._session_repository.create(session)
        token = self._jwt_provider.encode(SessionTokenEntity(
            session_id=session.id, secret=secret, issued_at=now,
        ))
        return LoginResultDTO(token=token)
