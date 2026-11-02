from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class LoginDTO:
    email: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class LoginResultDTO:
    token: str = field(repr=False)
