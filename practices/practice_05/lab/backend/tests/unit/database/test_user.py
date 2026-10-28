from __future__ import annotations

import pytest
from sqlalchemy import Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateTable

from app.infrastructure.database.models import UserORM


def test_username_is_required_and_has_no_default() -> None:
    column = UserORM.__table__.c.username
    assert not column.nullable
    assert column.type.length == 100
    assert column.default is None
    assert column.server_default is None


def test_email_is_unique() -> None:
    table = UserORM.__table__
    assert not table.c.email.nullable
    assert table.c.email.type.length == 254
    assert any(
        isinstance(constraint, UniqueConstraint)
        and list(constraint.columns.keys()) == ["email"]
        for constraint in table.constraints
    )


def test_role_is_integer_with_regular_user_default() -> None:
    column = UserORM.__table__.c.role
    assert isinstance(column.type, Integer)
    assert not column.nullable
    ddl = str(CreateTable(UserORM.__table__).compile(dialect=dialect()))
    assert "role INTEGER DEFAULT 1 NOT NULL" in ddl
    assert "is_active BOOLEAN DEFAULT true NOT NULL" in ddl
    assert UserORM.__table__.c.updated_at.onupdate is not None


@pytest.mark.parametrize("name, expression", [
    ("ck_users_role", "role IN (1, 2, 3)"),
    ("ck_users_email_canonical", "email = lower(btrim(email)) AND char_length(email) > 0"),
    ("ck_users_username_canonical", "username = btrim(username) AND char_length(username) > 0"),
    ("ck_users_display_name_not_blank", "display_name IS NULL OR char_length(btrim(display_name)) > 0"),
    ("ck_users_timestamps_order", "updated_at >= created_at"),
])
def test_user_constraints_are_emitted_in_postgresql_ddl(name: str, expression: str) -> None:
    ddl = str(CreateTable(UserORM.__table__).compile(dialect=dialect()))
    assert f"CONSTRAINT {name} CHECK ({expression})" in ddl
