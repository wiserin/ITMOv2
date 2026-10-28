from __future__ import annotations

from app.application.dto.login import LoginDTO, LoginResultDTO


class LoginUseCase:
    async def login(self, data: LoginDTO) -> LoginResultDTO:
        """Authenticate credentials and create a session; implementation follows later."""
        raise NotImplementedError("Login scenario is not implemented yet")
