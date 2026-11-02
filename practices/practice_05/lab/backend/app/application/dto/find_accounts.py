from __future__ import annotations

from dataclasses import dataclass

from app.application.dto.user import UserDTO


@dataclass(frozen=True, slots=True, kw_only=True)
class FindAccountsResultDTO:
    accounts: tuple[UserDTO, ...]
