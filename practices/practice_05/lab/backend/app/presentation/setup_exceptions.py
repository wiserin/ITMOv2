from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse

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
from app.presentation.logout_response import is_logout, logout_policy

type ErrorMapping = dict[type[BaseDomainException], tuple[int, str]]

DOMAIN_ERROR_MAPPING: ErrorMapping = {
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
        mappings = DOMAIN_ERROR_MAPPING.items()
        status_code, error = next(
            (
                response
                for exception, response in mappings
                if isinstance(exc, exception)
            ),
            (500, "internal_error"),
        )
        response = JSONResponse(
            status_code=status_code,
            content=jsonable_encoder({
                "error": error,
                "message": exc.message,
                "details": exc.details,
            }),
        )
        return logout_policy(
            request, response,
            authentication_failure=isinstance(
                exc, AuthenticationException,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
            request: Request,
            exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "type": error["type"],
                "loc": error["loc"],
                "msg": error["msg"],
            }
            for error in exc.errors()
        ]
        response = JSONResponse(
            status_code=400,
            content=jsonable_encoder({
                "error": "bad_request",
                "message": "Ошибка валидации данных.",
                "details": {"errors": errors},
            }),
        )
        return logout_policy(request, response)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if not is_logout(request):
            return await http_exception_handler(request, exc)
        headers = dict(exc.headers or {})
        if exc.status_code == 405:
            headers["Allow"] = "POST"
        response = JSONResponse(
            status_code=exc.status_code, headers=headers,
            content={
                "error": (
                    "method_not_allowed" if exc.status_code == 405
                    else "bad_request"
                ),
                "message": "Logout request rejected", "details": {},
            },
        )
        return logout_policy(request, response)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        if not is_logout(request):
            return PlainTextResponse("Internal Server Error", 500)
        response = JSONResponse(status_code=500, content={
            "error": "internal_error",
            "message": "Internal server error", "details": {},
        })
        return logout_policy(request, response)
