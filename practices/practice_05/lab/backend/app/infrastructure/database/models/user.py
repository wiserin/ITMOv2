from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Integer, func, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, VARCHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.general import Base

if TYPE_CHECKING:
    from .credential import CredentialORM
    from .session import SessionORM


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN (1, 2, 3)", name="ck_users_role"),
        CheckConstraint(
            "email = lower(btrim(email)) AND char_length(email) > 0",
            name="ck_users_email_canonical",
        ),
        CheckConstraint(
            "username = btrim(username) "
            "AND char_length(username) > 0",
            name="ck_users_username_canonical",
        ),
        CheckConstraint(
            "display_name IS NULL "
            "OR char_length(btrim(display_name)) > 0",
            name="ck_users_display_name_not_blank",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="ck_users_timestamps_order",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True,
    )
    email: Mapped[str] = mapped_column(VARCHAR(254), unique=True)
    username: Mapped[str] = mapped_column(VARCHAR(100))
    display_name: Mapped[str | None] = mapped_column(VARCHAR(100))
    role: Mapped[int] = mapped_column(
        Integer, server_default=text("1"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    credentials: Mapped[list[CredentialORM]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    sessions: Mapped[list[SessionORM]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
