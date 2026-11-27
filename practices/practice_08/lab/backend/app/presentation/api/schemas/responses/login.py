from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict

from app.application.dto.login import LoginResultDTO


class LoginResponse(BaseModel):
    """Successful login; the token is delivered through a cookie."""

    model_config = ConfigDict(strict=True, extra="forbid")

    @classmethod
    def from_dto(cls, dto: LoginResultDTO) -> Self:
        return cls()
