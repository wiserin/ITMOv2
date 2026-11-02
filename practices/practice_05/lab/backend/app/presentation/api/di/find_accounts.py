from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.find_accounts import FindAccountsUseCase
from app.presentation.api.di.repositories.user import UserRepositoryDI


def get_find_accounts_usecase(
        user_repository: UserRepositoryDI) -> FindAccountsUseCase:
    return FindAccountsUseCase(user_repository=user_repository)


FindAccountsUseCaseDI = Annotated[
    FindAccountsUseCase,
    Depends(get_find_accounts_usecase),
]
