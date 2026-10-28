from uuid import uuid4

import pytest

from app.application.dto.user import UserDTO
from app.application.usecases.base import BaseUseCase
from app.domain.enums.user_role import UserRole


@pytest.mark.parametrize("minimum, role, allowed", [
    (UserRole.USER, UserRole.USER, True),
    (UserRole.USER, UserRole.MODERATOR, True),
    (UserRole.USER, UserRole.ADMIN, True),
    (UserRole.MODERATOR, UserRole.USER, False),
    (UserRole.MODERATOR, UserRole.MODERATOR, True),
    (UserRole.MODERATOR, UserRole.ADMIN, True),
    (UserRole.ADMIN, UserRole.USER, False),
    (UserRole.ADMIN, UserRole.MODERATOR, False),
    (UserRole.ADMIN, UserRole.ADMIN, True),
])
def test_role_hierarchy(
        minimum: UserRole,
        role: UserRole,
        allowed: bool) -> None:
    use_case = BaseUseCase(min_permission=minimum)
    user = UserDTO(
        id=uuid4(), email="user@example.com", username="user",
        role=role, is_active=True,
    )
    assert use_case.authorize(user) is allowed


def test_default_access_level_is_user() -> None:
    assert BaseUseCase().access_level is UserRole.USER
