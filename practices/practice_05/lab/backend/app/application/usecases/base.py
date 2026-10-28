from __future__ import annotations

from app.application.dto.user import UserDTO
from app.domain.enums.user_role import UserRole


class BaseUseCase:
    def __init__(
            self,
            *,
            min_permission: UserRole = UserRole.USER) -> None:
        self.access_level = min_permission

    def authorize(self, user: UserDTO) -> bool:
        return self.access_level <= user.role
