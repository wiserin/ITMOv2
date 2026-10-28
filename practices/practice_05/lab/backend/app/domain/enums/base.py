from __future__ import annotations

from enum import IntEnum
from typing import Self

from app.domain.exceptions.entities import DataFormatException


class BaseIntEnum(IntEnum):
    def to_string(self) -> str:
        return self.name.lower()

    @classmethod
    def from_string(cls, value: str) -> Self:
        for member in cls:
            if member.to_string() == value:
                return member
        raise DataFormatException(details={"enum": cls.__name__, "value": value})
