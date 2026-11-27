from __future__ import annotations

from datetime import UTC, datetime

from app.application.dto.register import RegisterDTO
from app.application.usecases.base import BaseUseCase
from app.domain.entities.credential import CredentialEntity
from app.domain.entities.user import UserEntity
from app.domain.exceptions.entities import AlreadyExistsException
from app.domain.ports.secret import SecretManagerPort
from app.domain.repositories.credential import CredentialRepository
from app.domain.repositories.user import UserRepository


class RegisterUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository,
            credential_repository: CredentialRepository,
            secret_manager: SecretManagerPort) -> None:
        super().__init__()
        self._user_repository = user_repository
        self._credential_repository = credential_repository
        self._secret_manager = secret_manager

    async def register(self, data: RegisterDTO) -> None:
        password_hash = await self._secret_manager.hash_secret(
            data.password,
        )
        now = datetime.now(UTC)
        user = UserEntity(
            email=data.email.strip().lower(),
            username=data.username.strip(),
            display_name=(
                data.display_name.strip()
                if data.display_name is not None else None
            ),
            created_at=now,
            updated_at=now,
        )
        try:
            await self._user_repository.create(user)
        except AlreadyExistsException as exc:
            raise AlreadyExistsException(details={
                "entity": "user", "field": "email",
            }) from exc
        await self._credential_repository.create(CredentialEntity(
            user_id=user.id,
            password_hash=password_hash,
            created_at=now,
        ))
