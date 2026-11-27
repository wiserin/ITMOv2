from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta

from app.application.dto.user import UserDTO
from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import (
    AuthenticationException,
    NotFoundException,
)
from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


class AuthUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository,
            session_repository: SessionRepository,
            jwt_provider: JwtProviderPort,
            secret_manager: SecretManagerPort,
            session_idle_timeout_minutes: int,
            commit: Callable[[], Awaitable[None]]) -> None:
        super().__init__()
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._jwt_provider = jwt_provider
        self._secret_manager = secret_manager
        self._idle_timeout = timedelta(
            minutes=session_idle_timeout_minutes,
        )
        self._commit = commit

    async def authenticate(self, token: str) -> UserDTO:
        decoded = await asyncio.to_thread(
            self._jwt_provider.decode, token,
        )
        try:
            session = await self._session_repository.get_by_id(
                decoded.session_id,
            )
            session.ensure_usable()
            await self._secret_manager.verify_secret(
                decoded.secret, session.secret_hash,
            )
            # Lock owner before session, consistently with login.
            user = await self._user_repository.get_by_id(
                session.user_id, for_update=True,
            )
            session = await self._session_repository.get_by_id(
                session.id, for_update=True,
            )
            if not user.is_active:
                raise AuthenticationException(
                    details={"reason": "inactive_user"},
                )
            session = session.use(idle_timeout=self._idle_timeout)
            await self._session_repository.update(session)
        except NotFoundException as exc:
            raise AuthenticationException(
                details={"reason": "session_not_found"},
            ) from exc
        # Authentication usage survives a later business rollback/403.
        await self._commit()
        return UserDTO.from_entity(user)
