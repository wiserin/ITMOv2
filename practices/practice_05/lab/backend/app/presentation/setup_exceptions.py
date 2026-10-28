from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.exceptions.base import BaseDomainException
from app.domain.exceptions.entities import (
    AlreadyExistsException,
    AuthenticationException,
    ConflictException,
    DataFormatException,
    NotFoundException,
    NotImplementedException,
    PermissionException,
    ServiceUnavailableException,
)

DOMAIN_ERROR_MAPPING: dict[type[BaseDomainException], tuple[int, str]] = {
    AlreadyExistsException: (409, "conflict"),
    ConflictException: (409, "conflict"),
    DataFormatException: (400, "bad_request"),
    NotFoundException: (404, "not_found"),
    AuthenticationException: (401, "authentication_failed"),
    PermissionException: (403, "access_denied"),
    NotImplementedException: (501, "not_implemented"),
    ServiceUnavailableException: (503, "service_unavailable"),
}


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BaseDomainException)
    async def domain_exception_handler(
            request: Request,
            exc: BaseDomainException) -> JSONResponse:
        status_code, error = next(
            (response for exception, response in DOMAIN_ERROR_MAPPING.items() if isinstance(exc, exception)),
            (500, "internal_error"),
        )
        return JSONResponse(
            status_code=status_code,
            content=jsonable_encoder({
                "error": error, "message": exc.message, "details": exc.details,
            }),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
            request: Request,
            exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"type": error["type"], "loc": error["loc"], "msg": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=400,
            content=jsonable_encoder({
                "error": "bad_request", "message": "Ошибка валидации данных.",
                "details": {"errors": errors},
            }),
        )
