from __future__ import annotations

from pydantic import Field

from app.application.dto.login import LoginDTO
from app.presentation.api.schemas.common import BaseRequest, Email, Password


class LoginRequest(BaseRequest):
    email: Email = Field(description="Email пользователя")
    password: Password = Field(repr=False, description="Пароль без нормализации пробелов")

    def to_dto(self) -> LoginDTO:
        return LoginDTO(
            email=str(self.email), password=self.password.get_secret_value(),
        )
