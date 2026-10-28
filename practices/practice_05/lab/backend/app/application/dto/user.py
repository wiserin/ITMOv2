from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDTO:
    id: UUID
    email: str
    username: str
    role: int
    is_active: bool
    display_name: str | None = None
