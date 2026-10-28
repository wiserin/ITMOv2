from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from app.infrastructure.database.models import SessionORM


def test_open_session_index_is_partial_and_not_unique() -> None:
    index = next(
        index for index in SessionORM.__table__.indexes
        if index.name == "ix_sessions_open_expires_at"
    )
    ddl = str(CreateIndex(index).compile(dialect=dialect()))
    assert ddl == (
        "CREATE INDEX ix_sessions_open_expires_at "
        "ON sessions (expires_at) WHERE closed_at IS NULL"
    )


def test_expiration_requires_application_value() -> None:
    column = SessionORM.__table__.c.expires_at
    assert not column.nullable
    assert column.default is None
    assert column.server_default is None


@pytest.mark.parametrize("name, expression", [
    (
        "ck_sessions_secret_not_blank",
        "char_length(btrim(secret)) > 0",
    ),
    (
        "ck_sessions_secret_hash_not_blank",
        "char_length(btrim(secret_hash)) > 0",
    ),
    ("ck_sessions_last_used_at", "last_used_at >= created_at"),
    ("ck_sessions_expires_at", "expires_at > last_used_at"),
    (
        "ck_sessions_closed_at",
        "closed_at IS NULL OR closed_at >= last_used_at",
    ),
])
def test_session_constraints_are_emitted_in_postgresql_ddl(
        name: str,
        expression: str) -> None:
    ddl = str(
        CreateTable(SessionORM.__table__).compile(dialect=dialect()),
    )
    assert f"CONSTRAINT {name} CHECK ({expression})" in ddl


def test_secrets_are_required_and_excluded_from_repr() -> None:
    table = SessionORM.__table__
    assert not table.c.secret.nullable
    assert not table.c.secret_hash.nullable
    session = SessionORM(
        id=uuid4(), secret="private-secret",
        secret_hash="private-hash",
    )
    for representation in (repr(session), str(session)):
        assert "private-secret" not in representation
        assert "private-hash" not in representation
