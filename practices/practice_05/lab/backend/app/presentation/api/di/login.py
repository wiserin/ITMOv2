from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.application.dto.login import LoginDTO, LoginResultDTO
from app.application.usecases.login import LoginUseCase


class UnconfiguredLoginUseCase(LoginUseCase):
    async def login(self, data: LoginDTO) -> LoginResultDTO:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Login use case is not configured",
        )


def get_login_usecase() -> LoginUseCase:
    return UnconfiguredLoginUseCase()

LoginUseCaseDI = Annotated[
    LoginUseCase,
    Depends(get_login_usecase),
]
