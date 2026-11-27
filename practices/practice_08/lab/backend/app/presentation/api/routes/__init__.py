from fastapi import APIRouter

from app.presentation.api.schemas.responses.error import ErrorResponse

from .account import router as account_router
from .auth import router as auth_router

router_v1 = APIRouter(
    prefix="/v1",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Некорректные входные данные",
        },
        "4XX": {
            "model": ErrorResponse,
            "description": "Доменная ошибка запроса",
        },
    },
)
router_v1.include_router(auth_router)
router_v1.include_router(account_router)
