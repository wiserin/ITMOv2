from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.application.dto.register import RegisterDTO
from app.application.usecases.register import RegisterUseCase


class UnconfiguredRegisterUseCase(RegisterUseCase):
    async def register(self, data: RegisterDTO) -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Registration use case is not configured",
        )


def get_register_usecase() -> RegisterUseCase:
    return UnconfiguredRegisterUseCase()


RegisterUseCaseDI = Annotated[
    RegisterUseCase,
    Depends(get_register_usecase),
]
