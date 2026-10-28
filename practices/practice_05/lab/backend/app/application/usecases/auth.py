from __future__ import annotations

from app.application.dto.user import UserDTO
from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import NotImplementedException
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


class AuthUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository,
            session_repository: SessionRepository) -> None:
        super().__init__()
        self._user_repository = user_repository
        self._session_repository = session_repository

    async def authenticate(self, token: str) -> UserDTO:
        """Validate the session (not implemented)."""
        raise NotImplementedException(
            details={"operation": "authenticate"},
        )
