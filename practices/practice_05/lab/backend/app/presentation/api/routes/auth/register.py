from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse

from app.presentation.api.di.register import RegisterUseCaseDI
from app.presentation.api.schemas.requests.register import RegisterRequest
from app.presentation.api.schemas.responses.error import ErrorResponse

router = APIRouter()


@router.post(
    "/register",
    name="auth_register",
    status_code=status.HTTP_303_SEE_OTHER,
    response_class=RedirectResponse,
    summary="Регистрация и перенаправление на вход",
    responses={
        status.HTTP_303_SEE_OTHER: {
            "description": "Пользователь создан; следующий шаг — вход",
            "headers": {"Location": {"schema": {"type": "string"}}},
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse, "description": "Email уже зарегистрирован",
        },
        status.HTTP_501_NOT_IMPLEMENTED: {
            "model": ErrorResponse, "description": "Сценарий регистрации ещё не подключён",
        },
    },
)
async def register(
        data: RegisterRequest,
        request: Request,
        use_case: RegisterUseCaseDI) -> RedirectResponse:
    await use_case.register(data.to_dto())
    return RedirectResponse(
        url=str(request.url_for("auth_login")),
        status_code=status.HTTP_303_SEE_OTHER,
    )
