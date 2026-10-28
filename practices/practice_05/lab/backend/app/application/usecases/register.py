from __future__ import annotations

from app.application.dto.register import RegisterDTO


class RegisterUseCase:
    async def register(self, data: RegisterDTO) -> None:
        """Create a regular user and current credential; implementation follows later."""
        raise NotImplementedError("Registration scenario is not implemented yet")
