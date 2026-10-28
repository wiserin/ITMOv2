from __future__ import annotations

from app.application.dto.user import UserDTO


class AuthUseCase:
    async def authenticate(self, token: str) -> UserDTO:
        """Validate and prolong a session and return its owner; implementation follows later."""
        raise NotImplementedError("Authentication scenario is not implemented yet")
