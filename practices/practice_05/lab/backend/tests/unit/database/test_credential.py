from __future__ import annotations

from uuid import uuid4

from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from app.infrastructure.database.models import CredentialORM


def test_only_current_password_is_unique_per_user() -> None:
    index = next(
        index for index in CredentialORM.__table__.indexes
        if index.name == "uq_credentials_current_user"
    )
    ddl = str(CreateIndex(index).compile(dialect=dialect()))
    assert ddl == (
        "CREATE UNIQUE INDEX uq_credentials_current_user "
        "ON credentials (user_id) WHERE is_current = true"
    )
    assert not CredentialORM.__table__.c.user_id.unique


def test_password_hash_is_required_and_nonempty() -> None:
    column = CredentialORM.__table__.c.password_hash
    assert not column.nullable
    table = CreateTable(CredentialORM.__table__)
    ddl = str(table.compile(dialect=dialect()))
    assert "is_current BOOLEAN DEFAULT true NOT NULL" in ddl
    assert (
        "CONSTRAINT ck_credentials_password_hash_not_blank "
        "CHECK (char_length(btrim(password_hash)) > 0)"
    ) in ddl


def test_repr_does_not_expose_password_hash() -> None:
    credential = CredentialORM(
        id=uuid4(), password_hash="private-password-hash",
    )
    assert "private-password-hash" not in repr(credential)
    assert "private-password-hash" not in str(credential)
