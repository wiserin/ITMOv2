from __future__ import annotations

from app.application.dto.find_accounts import FindAccountsResultDTO
from app.application.dto.pagination import PaginationDTO
from app.application.dto.user import UserDTO
from app.application.usecases.base import BaseUseCase
from app.domain.enums.user_role import UserRole
from app.domain.exceptions.entities import PermissionException
from app.domain.repositories.user import UserRepository


class FindAccountsUseCase(BaseUseCase):
    def __init__(
            self,
            *,
            user_repository: UserRepository) -> None:
        super().__init__(min_permission=UserRole.MODERATOR)
        self._user_repository = user_repository

    async def find_accounts(
            self,
            username_prefix: str,
            pagination: PaginationDTO,
            requester: UserDTO) -> FindAccountsResultDTO:
        if not self.authorize(requester):
            raise PermissionException(details={
                "entity": "user",
                "operation": "find_by_username_prefix",
                "min_permission": int(self.access_level),
            })
        repository = self._user_repository
        accounts = await repository.find_by_username_prefix(
            username_prefix,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        return FindAccountsResultDTO(
            accounts=tuple(
                UserDTO.from_entity(account) for account in accounts
            ),
        )
