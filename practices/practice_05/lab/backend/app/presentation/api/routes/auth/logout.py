from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, Security
from fastapi.security import APIKeyCookie

from app.domain.exceptions.entities import (
    AuthenticationException,
    DataFormatException,
    PermissionException,
)
from app.presentation.api.di.logout import LogoutUseCaseDI
from app.presentation.logout_response import logout_policy

router = APIRouter()
cookie_security = APIKeyCookie(
    name="session_token", scheme_name="SessionCookie",
    auto_error=False,
)


async def validate_input(request: Request) -> None:
    values = request.headers.getlist("x-animemap-logout")
    if values != ["1"]:
        raise PermissionException(
            details={"reason": "csrf_check_failed"},
        )
    if request.url.query or await request.body():
        raise DataFormatException(details={"reason": "invalid_input"})
    request.state.logout_credential_check = True


CookieToken = Annotated[str | None, Security(cookie_security)]


async def credential(
        validated: Annotated[None, Depends(validate_input)],
        token: CookieToken) -> str:
    if not token:
        raise AuthenticationException(
            details={"reason": "missing_session_cookie"},
        )
    return token


@router.post(
    "/logout", name="auth_logout", operation_id="auth_logout",
    status_code=204,
    responses={code: {"description": text} for code, text in [
        (400, "Invalid input or hash"), (401, "Invalid credential"),
        (403, "CSRF rejected"), (405, "Allow: POST"),
        (500, "Internal error"), (503, "Storage unavailable"),
    ]},
    openapi_extra={"parameters": [{
        "in": "header", "name": "X-AnimeMap-Logout",
        "required": True, "schema": {"type": "string", "enum": ["1"]},
    }]},
)
async def logout(
        request: Request,
        token: Annotated[str, Depends(credential)],
        use_case: LogoutUseCaseDI) -> Response:
    await use_case.logout(token)
    return logout_policy(request, Response(status_code=204))
