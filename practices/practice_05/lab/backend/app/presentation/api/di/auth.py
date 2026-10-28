from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyCookie

from app.application.dto.user import UserDTO
from app.application.usecases.auth import AuthUseCase
from app.domain.exceptions.entities import AuthenticationException
from app.presentation.api.cookies import SESSION_COOKIE_NAME

session_cookie = APIKeyCookie(
    name=SESSION_COOKIE_NAME, scheme_name="SessionCookie", auto_error=False,
)


def get_auth_usecase() -> AuthUseCase:
    return AuthUseCase()


async def get_authenticated_user(
        token: Annotated[str | None, Security(session_cookie)],
        use_case: Annotated[AuthUseCase, Depends(get_auth_usecase)]) -> UserDTO:
    if not token:
        raise AuthenticationException(details={"reason": "missing_session_cookie"})
    user = await use_case.authenticate(token)
    if not user.is_active:
        raise AuthenticationException(details={"entity": "user", "reason": "inactive"})
    return user


AuthUseCaseDI = Annotated[
    UserDTO,
    Depends(get_authenticated_user),
]
