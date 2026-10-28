from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.register import RegisterUseCase


def get_register_usecase() -> RegisterUseCase:
    return RegisterUseCase()


RegisterUseCaseDI = Annotated[
    RegisterUseCase,
    Depends(get_register_usecase),
]
