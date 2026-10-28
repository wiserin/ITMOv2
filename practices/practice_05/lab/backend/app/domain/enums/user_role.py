from app.domain.enums.base import BaseIntEnum


class UserRole(BaseIntEnum):
    USER = 1
    MODERATOR = 2
    ADMIN = 3
