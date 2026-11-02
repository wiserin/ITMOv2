import asyncio
from datetime import UTC, datetime

from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import (
    AuthenticationException,
    NotFoundException,
)
from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


class LogoutUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository,
            session_repository: SessionRepository,
            jwt_provider: JwtProviderPort,
            secret_manager: SecretManagerPort) -> None:
        super().__init__()
        self._user_repository = user_repository
        self._session_repository = session_repository
        self._jwt_provider = jwt_provider
        self._secret_manager = secret_manager

    async def logout(self, token: str) -> None:
        decoded = await asyncio.to_thread(
            self._jwt_provider.decode, token,
        )
        try:
            initial = await self._session_repository.get_by_id(
                decoded.session_id,
            )
            initial.ensure_usable()
            await self._secret_manager.verify_secret(
                decoded.secret, initial.secret_hash,
            )
            owner_id = initial.user_id
            verified_hash = initial.secret_hash
            user = await self._user_repository.get_by_id(
                owner_id, for_update=True,
            )
            current = await self._session_repository.get_by_id(
                initial.id, for_update=True,
            )
            if current.user_id != owner_id or user.id != owner_id:
                raise AuthenticationException(
                    details={"reason": "session_not_found"},
                )
            if current.secret_hash != verified_hash:
                raise AuthenticationException(
                    details={"reason": "invalid_secret"},
                )
            now = datetime.now(UTC)
            current.ensure_usable(now=now)
            await self._session_repository.update(
                current.close(now=now),
            )
        except NotFoundException as exc:
            raise AuthenticationException(
                details={"reason": "session_not_found"},
            ) from exc
