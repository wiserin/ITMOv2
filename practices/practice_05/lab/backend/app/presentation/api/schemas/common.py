from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
)


def normalize_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


Email = Annotated[
    EmailStr, BeforeValidator(normalize_email), Field(max_length=254),
]
Password = Annotated[SecretStr, Field(min_length=1)]


class BaseRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
