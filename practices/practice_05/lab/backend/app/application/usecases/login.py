from __future__ import annotations

from app.application.dto.login import LoginDTO, LoginResultDTO
from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import NotImplementedException


class LoginUseCase(BaseUseCase):
    def __init__(self) -> None:
        super().__init__()

    async def login(self, data: LoginDTO) -> LoginResultDTO:
        """Authenticate credentials and create a session; implementation follows later."""
        raise NotImplementedException(details={"operation": "login"})
