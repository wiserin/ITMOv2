from __future__ import annotations

from app.application.dto.register import RegisterDTO
from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import NotImplementedException
from app.domain.repositories.credential import CredentialRepository
from app.domain.repositories.user import UserRepository


class RegisterUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository,
            credential_repository: CredentialRepository) -> None:
        super().__init__()
        self._user_repository = user_repository
        self._credential_repository = credential_repository

    async def register(self, data: RegisterDTO) -> None:
        """Create a user and current credential (not implemented)."""
        raise NotImplementedException(
            details={"operation": "register"},
        )
