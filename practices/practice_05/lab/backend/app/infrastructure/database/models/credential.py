from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import TEXT, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.general import Base

if TYPE_CHECKING:
    from .user import UserORM


class CredentialORM(Base):
    __tablename__ = "credentials"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(password_hash)) > 0",
            name="ck_credentials_password_hash_not_blank",
        ),
        Index("ix_credentials_user_id", "user_id"),
        Index(
            "uq_credentials_current_user", "user_id", unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", onupdate="NO ACTION"),
    )
    password_hash: Mapped[str] = mapped_column(TEXT)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(),
    )

    user: Mapped[UserORM] = relationship(back_populates="credentials")
