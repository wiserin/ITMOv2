from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.application.usecases.find_accounts import FindAccountsUseCase
from app.domain.repositories.user import UserRepository
from app.infrastructure.database.repositories.user import (
    UnconfiguredUserRepositoryAdapter,
)


def get_user_repository() -> UserRepository:
    return UnconfiguredUserRepositoryAdapter()


def get_find_accounts_usecase(
        user_repository: Annotated[UserRepository, Depends(get_user_repository)]) -> FindAccountsUseCase:
    return FindAccountsUseCase(user_repository=user_repository)


FindAccountsUseCaseDI = Annotated[
    FindAccountsUseCase,
    Depends(get_find_accounts_usecase),
]
