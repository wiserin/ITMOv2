from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.presentation.api.di.entities.user import AuthUseCaseDI
from app.presentation.api.di.find_accounts import (
    FindAccountsUseCaseDI,
)
from app.presentation.api.schemas.requests.account import (
    UsernamePrefix,
)
from app.presentation.api.schemas.requests.pagination import (
    PaginationRequest,
)
from app.presentation.api.schemas.responses.account import (
    FindAccountsResponse,
)
from app.presentation.api.schemas.responses.error import ErrorResponse

router = APIRouter()


@router.get(
    "/find/{username_prefix}",
    name="account_find",
    summary="Поиск аккаунтов по префиксу username",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Сессия отсутствует или недействительна",
        },
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Требуются права модератора",
        },
        status.HTTP_501_NOT_IMPLEMENTED: {
            "model": ErrorResponse,
            "description": "Аутентификация ещё не реализована",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "PostgreSQL временно недоступен",
        },
    },
)
async def find(
        username_prefix: UsernamePrefix,
        pagination: Annotated[PaginationRequest, Query()],
        user: AuthUseCaseDI,
        use_case: FindAccountsUseCaseDI,
        response: Response) -> FindAccountsResponse:
    result = await use_case.find_accounts(
        username_prefix=username_prefix,
        pagination=pagination.to_dto(),
        requester=user,
    )
    response.headers["Cache-Control"] = "no-store"
    return FindAccountsResponse.from_dto(result)
