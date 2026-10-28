from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from argon2 import PasswordHasher
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.infrastructure.database.models import (
    CredentialORM,
    SessionORM,
    UserORM,
)

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_DATABASE_URL must point to a migrated PostgreSQL",
)


def run_check(
        check: Callable[[AsyncSession], Awaitable[None]]) -> None:
    async def run() -> None:
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
        try:
            async with engine.connect() as connection:
                transaction = await connection.begin()
                try:
                    async with AsyncSession(
                        bind=connection,
                        join_transaction_mode="create_savepoint",
                        expire_on_commit=False,
                    ) as session:
                        await check(session)
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    asyncio.run(run())


def test_bootstrap_root() -> None:
    async def check(session: AsyncSession) -> None:
        root = (await session.scalars(
            select(UserORM).where(UserORM.email == "root@example.com")
            .options(
                selectinload(UserORM.credentials).selectinload(
                    CredentialORM.user,
                ),
                selectinload(UserORM.sessions),
            )
        )).one()
        assert root.username == "root"
        assert root.role == 3
        assert root.is_active
        assert root.id.version == 4
        assert root.created_at.tzinfo is not None
        assert root.updated_at >= root.created_at
        assert root.sessions == []
        assert len(root.credentials) == 1
        credential = root.credentials[0]
        assert credential.is_current
        assert credential.user is root
        assert credential.password_hash.startswith("$argon2id$")
        assert PasswordHasher().verify(
            credential.password_hash, "root",
        )
        assert credential.password_hash not in repr(credential)

    run_check(check)


def test_password_history_allows_only_one_current_password() -> None:
    async def check(session: AsyncSession) -> None:
        root_id = (await session.scalars(
            select(UserORM.id)
            .where(UserORM.email == "root@example.com")
        )).one()
        for _ in range(2):
            session.add(CredentialORM(
                id=uuid4(), user_id=root_id,
                password_hash="historical-hash",
                is_current=False,
            ))
        await session.flush()
        with pytest.raises(
            IntegrityError, match="uq_credentials_current_user",
        ):
            async with session.begin_nested():
                session.add(CredentialORM(
                    id=uuid4(), user_id=root_id,
                    password_hash="second-current-hash",
                    is_current=True,
                ))
                await session.flush()
        current = (await session.scalars(select(CredentialORM).where(
            CredentialORM.user_id == root_id,
            CredentialORM.is_current.is_(True),
        ))).one()
        current.is_current = False
        await session.flush()
        session.add(CredentialORM(
            id=uuid4(), user_id=root_id,
            password_hash="replacement-hash", is_current=True,
        ))
        await session.flush()

    run_check(check)


def test_relationships_and_database_delete_cascade() -> None:
    async def check(session: AsyncSession) -> None:
        now = datetime.now(UTC)
        user = UserORM(
            id=uuid4(), email=f"{uuid4()}@example.com",
            username="test",
        )
        user.credentials.append(CredentialORM(
            id=uuid4(), password_hash="test-hash",
        ))
        user.sessions.append(SessionORM(
            id=uuid4(), secret="session-secret",
            secret_hash="session-secret-hash",
            created_at=now, last_used_at=now,
            expires_at=now + timedelta(minutes=30),
        ))
        session.add(user)
        await session.flush()
        user_id = user.id
        assert user.role == 1
        assert user.is_active
        assert user.sessions[0].user_id == user_id
        assert "session-secret" not in repr(user.sessions[0])
        await session.execute(
            delete(UserORM).where(UserORM.id == user_id),
        )
        for model in (CredentialORM, SessionORM):
            count = await session.scalar(
                select(func.count()).select_from(model)
                .where(model.user_id == user_id),
            )
            assert count == 0

    run_check(check)


@pytest.mark.parametrize("changes", [
    {"username": None},
    {"username": ""},
    {"username": " padded "},
    {"role": 4},
    {"email": "UPPER@example.com"},
])
def test_user_constraints(changes: dict[str, object]) -> None:
    async def check(session: AsyncSession) -> None:
        values = {
            "id": uuid4(), "email": f"{uuid4()}@example.com",
            "username": "test",
        }
        values.update(changes)
        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                session.add(UserORM(**values))
                await session.flush()

    run_check(check)


@pytest.mark.parametrize("invalid_field", [
    "expires_at", "last_used_at", "closed_at",
])
def test_session_timestamp_constraints(invalid_field: str) -> None:
    async def check(session: AsyncSession) -> None:
        root_id = (await session.scalars(
            select(UserORM.id)
            .where(UserORM.email == "root@example.com")
        )).one()
        now = datetime.now(UTC)
        values = {
            "id": uuid4(), "user_id": root_id, "secret": "secret",
            "secret_hash": "hash", "created_at": now,
            "last_used_at": now,
            "expires_at": now + timedelta(minutes=30),
        }
        values[invalid_field] = now - timedelta(seconds=1)
        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                session.add(SessionORM(**values))
                await session.flush()

    run_check(check)
