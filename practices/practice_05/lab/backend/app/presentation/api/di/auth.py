from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyCookie

from app.application.dto.user import UserDTO
from app.application.usecases.auth import AuthUseCase
from app.presentation.api.cookies import SESSION_COOKIE_NAME

session_cookie = APIKeyCookie(
    name=SESSION_COOKIE_NAME, scheme_name="SessionCookie", auto_error=False,
)


class UnconfiguredAuthUseCase(AuthUseCase):
    async def authenticate(self, token: str) -> UserDTO:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Authentication use case is not configured",
        )


def get_auth_usecase() -> AuthUseCase:
    return UnconfiguredAuthUseCase()


async def get_authenticated_user(
        token: Annotated[str | None, Security(session_cookie)],
        use_case: Annotated[AuthUseCase, Depends(get_auth_usecase)]) -> UserDTO:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session cookie is required",
        )
    return await use_case.authenticate(token)


AuthUseCaseDI = Annotated[
    UserDTO,
    Depends(get_authenticated_user),
]
