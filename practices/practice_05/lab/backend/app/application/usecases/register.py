from __future__ import annotations

from app.application.dto.register import RegisterDTO
from app.application.usecases.base import BaseUseCase
from app.domain.exceptions.entities import NotImplementedException


class RegisterUseCase(BaseUseCase):
    def __init__(self) -> None:
        super().__init__()

    async def register(self, data: RegisterDTO) -> None:
        """Create a regular user and current credential; implementation follows later."""
        raise NotImplementedException(details={"operation": "register"})
