from pydantic import Field

from app.application.dto.pagination import PaginationDTO
from app.presentation.api.schemas.common import BaseRequest


class PaginationRequest(BaseRequest):
    limit: int = Field(default=20, ge=1, le=100, strict=False)
    offset: int = Field(default=0, ge=0, le=10_000, strict=False)

    def to_dto(self) -> PaginationDTO:
        return PaginationDTO(limit=self.limit, offset=self.offset)
