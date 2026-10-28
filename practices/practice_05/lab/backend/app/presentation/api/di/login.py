from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.login import LoginUseCase


def get_login_usecase() -> LoginUseCase:
    return LoginUseCase()

LoginUseCaseDI = Annotated[
    LoginUseCase,
    Depends(get_login_usecase),
]
