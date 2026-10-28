from __future__ import annotations

from app.application.dto.login import LoginDTO, LoginResultDTO
from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import NotImplementedException
from app.domain.repositories.credential import CredentialRepository
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


class LoginUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository,
            credential_repository: CredentialRepository,
            session_repository: SessionRepository) -> None:
        super().__init__()
        self._user_repository = user_repository
        self._credential_repository = credential_repository
        self._session_repository = session_repository

    async def login(self, data: LoginDTO) -> LoginResultDTO:
        """Authenticate and create a session (not implemented)."""
        raise NotImplementedException(details={"operation": "login"})
