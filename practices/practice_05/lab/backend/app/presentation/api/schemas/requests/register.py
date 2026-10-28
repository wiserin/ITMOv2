from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from app.application.dto.register import RegisterDTO
from app.presentation.api.schemas.common import BaseRequest, Email, Password

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class RegisterRequest(BaseRequest):
    email: Email
    username: Name
    password: Password = Field(repr=False, description="Исходный пароль, не хэш")
    display_name: Name | None = None

    def to_dto(self) -> RegisterDTO:
        return RegisterDTO(
            email=str(self.email), username=self.username,
            password=self.password.get_secret_value(), display_name=self.display_name,
        )
