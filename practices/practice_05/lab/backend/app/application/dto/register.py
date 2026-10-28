from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterDTO:
    email: str
    username: str
    password: str = field(repr=False)
    display_name: str | None = None
