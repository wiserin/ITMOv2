from __future__ import annotations

import pytest
from sqlalchemy import TIMESTAMP, inspect
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.infrastructure.database.models import (
    Base,
    CredentialORM,
    SessionORM,
    UserORM,
)


@pytest.mark.parametrize(
    "model", [UserORM, CredentialORM, SessionORM],
)
def test_primary_key_is_external_uuid(model: type[Base]) -> None:
    table = model.__table__
    assert list(table.primary_key.columns.keys()) == ["id"]
    column = table.c.id
    assert isinstance(column.type, PG_UUID)
    assert column.type.as_uuid
    assert not column.nullable
    assert column.default is None
    assert column.server_default is None


@pytest.mark.parametrize("model, field", [
    (UserORM, "created_at"),
    (UserORM, "updated_at"),
    (CredentialORM, "created_at"),
    (SessionORM, "created_at"),
    (SessionORM, "last_used_at"),
    (SessionORM, "closed_at"),
    (SessionORM, "expires_at"),
])
def test_timestamps_preserve_timezone(
        model: type[Base],
        field: str) -> None:
    column = model.__table__.c[field]
    assert isinstance(column.type, TIMESTAMP)
    assert column.type.timezone
    assert column.nullable == (field == "closed_at")


@pytest.mark.parametrize("model, collection", [
    (CredentialORM, "credentials"),
    (SessionORM, "sessions"),
])
def test_user_relationship_and_database_cascade(
        model: type[Base],
        collection: str) -> None:
    table = model.__table__
    assert table.metadata is Base.metadata
    column = table.c.user_id
    assert isinstance(column.type, PG_UUID)
    assert not column.nullable
    foreign_key, = column.foreign_keys
    assert foreign_key.target_fullname == "users.id"
    assert foreign_key.ondelete == "CASCADE"
    assert foreign_key.onupdate == "NO ACTION"

    relationship = inspect(UserORM).relationships[collection]
    assert relationship.mapper.class_ is model
    assert relationship.uselist
    assert relationship.back_populates == "user"
    assert relationship.passive_deletes
    assert "delete-orphan" in relationship.cascade
    owner = inspect(model).relationships["user"]
    assert owner.mapper.class_ is UserORM
    assert not owner.uselist
    assert owner.back_populates == collection
