from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.application.dto.find_accounts import FindAccountsResultDTO
from app.application.dto.user import UserDTO
from app.presentation.api.schemas.enums.user_role import (
    UserRoleResponse,
)


class AccountResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    id: UUID
    email: str
    username: str
    display_name: str | None
    role: UserRoleResponse
    is_active: bool

    @classmethod
    def from_dto(cls, dto: UserDTO) -> Self:
        return cls(
            id=dto.id,
            email=dto.email,
            username=dto.username,
            display_name=dto.display_name,
            role=UserRoleResponse.from_domain(dto.role),
            is_active=dto.is_active,
        )


class FindAccountsResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    accounts: list[AccountResponse]

    @classmethod
    def from_dto(cls, dto: FindAccountsResultDTO) -> Self:
        return cls(accounts=[
            AccountResponse.from_dto(account)
            for account in dto.accounts
        ])
