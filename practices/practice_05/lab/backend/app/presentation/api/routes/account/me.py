from fastapi import APIRouter, Response, status

from app.presentation.api.di.entities.user import AuthUseCaseDI
from app.presentation.api.schemas.responses.account import (
    AccountResponse,
)
from app.presentation.api.schemas.responses.error import ErrorResponse

router = APIRouter()


@router.get(
    "/me", name="account_me", summary="Текущий аккаунт",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Сессия отсутствует или недействительна",
        },
        status.HTTP_501_NOT_IMPLEMENTED: {
            "model": ErrorResponse,
            "description": "Аутентификация ещё не подключена",
        },
    },
)
async def me(
        user: AuthUseCaseDI,
        response: Response) -> AccountResponse:
    response.headers["Cache-Control"] = "no-store"
    return AccountResponse.from_dto(user)
