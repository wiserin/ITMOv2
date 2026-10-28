from __future__ import annotations

from app.application.dto.user import UserDTO
from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import NotImplementedException


class AuthUseCase(BaseUseCase):
    def __init__(self) -> None:
        super().__init__()

    async def authenticate(self, token: str) -> UserDTO:
        """Validate and prolong a session and return its owner; implementation follows later."""
        raise NotImplementedException(details={"operation": "authenticate"})
