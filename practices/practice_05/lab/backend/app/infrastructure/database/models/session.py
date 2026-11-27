from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import TEXT, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.general import Base

if TYPE_CHECKING:
    from .user import UserORM


class SessionORM(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(secret_hash)) > 0",
            name="ck_sessions_secret_hash_not_blank",
        ),
        CheckConstraint(
            "last_used_at >= created_at",
            name="ck_sessions_last_used_at",
        ),
        CheckConstraint(
            "expires_at > last_used_at",
            name="ck_sessions_expires_at",
        ),
        CheckConstraint(
            "closed_at IS NULL OR closed_at >= last_used_at",
            name="ck_sessions_closed_at",
        ),
        Index("ix_sessions_user_id", "user_id"),
        Index(
            "ix_sessions_open_expires_at", "expires_at",
            postgresql_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "users.id", ondelete="CASCADE", onupdate="NO ACTION",
        ),
    )
    secret_hash: Mapped[str] = mapped_column(TEXT)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(),
    )
    last_used_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(),
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
    )

    user: Mapped[UserORM] = relationship(
        back_populates="sessions", lazy="raise",
    )
