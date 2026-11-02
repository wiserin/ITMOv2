from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.presentation.api.cookies import SESSION_COOKIE_NAME
from app.presentation.api.di.login import LoginUseCaseDI
from app.presentation.api.schemas.requests.login import LoginRequest
from app.presentation.api.schemas.responses.error import ErrorResponse
from app.presentation.api.schemas.responses.login import LoginResponse

router = APIRouter()


@router.post(
    "/login",
    name="auth_login",
    summary="Вход по email и паролю",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": (
                "Неверные данные или неактивный пользователь"
            ),
        },
        status.HTTP_501_NOT_IMPLEMENTED: {
            "model": ErrorResponse,
            "description": "Сценарий входа ещё не подключён",
        },
    },
)
async def login(
        data: LoginRequest,
        response: Response,
        use_case: LoginUseCaseDI) -> LoginResponse:
    result = await use_case.login(data.to_dto())
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=result.token,
        secure=True,
        httponly=True,
        samesite="lax",
        path="/"
    )
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse.from_dto(result)
