from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.domain.entities.credential import CredentialEntity
from app.domain.entities.session import SessionEntity
from app.domain.entities.user import UserEntity
from app.domain.enums.user_role import UserRole
from app.domain.exceptions.entities import (
    AlreadyExistsException,
    ConflictException,
    DataFormatException,
    NotFoundException,
)
from app.infrastructure.database.models import (
    CredentialORM,
    SessionORM,
    UserORM,
)
from app.infrastructure.database.repositories.credential import (
    SQLAlchemyCredentialRepositoryAdapter,
)
from app.infrastructure.database.repositories.session import (
    SQLAlchemySessionRepositoryAdapter,
)
from app.infrastructure.database.repositories.user import (
    SQLAlchemyUserRepositoryAdapter,
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
                        expire_on_commit=False,
                        autoflush=False,
                        join_transaction_mode="create_savepoint",
                    ) as session:
                        await check(session)
                finally:
                    await transaction.rollback()
        finally:
            await engine.dispose()

    asyncio.run(run())


def new_user(*, username: str = "repository-user") -> UserEntity:
    now = datetime.now(UTC)
    return UserEntity(
        email=f"{uuid4()}@example.com", username=username,
        created_at=now, updated_at=now,
    )


def new_session(user_id: UUID) -> SessionEntity:
    now = datetime.now(UTC)
    return SessionEntity(
        user_id=user_id,
        secret_hash="private-secret-hash",
        created_at=now, last_used_at=now,
        expires_at=now + timedelta(minutes=20),
    )


def test_user_crud_roundtrip_and_missing_row() -> None:
    async def check(session: AsyncSession) -> None:
        repository = SQLAlchemyUserRepositoryAdapter(session=session)
        entity = new_user()
        assert await repository.create(entity) == entity
        assert await repository.get_by_id(
            entity.id, for_update=True,
        ) == entity
        assert await repository.get_by_email(
            entity.email, for_update=True,
        ) == entity
        changed = replace(
            entity, username="updated-user", display_name="Updated",
            role=UserRole.MODERATOR,
            updated_at=entity.updated_at + timedelta(seconds=1),
        )
        assert await repository.update(changed) == changed
        assert await repository.get_by_id(entity.id) == changed
        assert await repository.delete(changed) == changed
        with pytest.raises(NotFoundException) as error:
            await repository.get_by_id(entity.id)
        assert error.value.details == {
            "entity": "user", "id": str(entity.id),
        }

    run_check(check)


def test_prefix_search_case_order_and_pagination() -> None:
    async def check(session: AsyncSession) -> None:
        repository = SQLAlchemyUserRepositoryAdapter(session=session)
        prefix = f"repo-{uuid4().hex}"
        entities = [
            new_user(username=prefix + suffix)
            for suffix in ("a", "a", "ab", "A", "b")
        ]
        for entity in reversed(entities):
            await repository.create(entity)
        expected = sorted(
            entities[:3],
            key=lambda entity: (entity.username, entity.id),
        )
        assert await repository.find_by_username_prefix(
            prefix + "a", limit=10, offset=0,
        ) == tuple(expected)
        assert await repository.find_by_username_prefix(
            prefix + "a", limit=1, offset=1,
        ) == (expected[1],)
        assert await repository.find_by_username_prefix(
            prefix + "a", limit=10, offset=3,
        ) == ()

    run_check(check)


def test_user_update_preserves_explicit_timestamp() -> None:
    async def check(session: AsyncSession) -> None:
        repository = SQLAlchemyUserRepositoryAdapter(session=session)
        entity = await repository.create(new_user())
        changed = replace(
            entity, display_name="Changed", role=UserRole.MODERATOR,
        )
        assert await repository.update(changed) == changed
        assert await repository.get_by_id(entity.id) == changed

    run_check(check)


@pytest.mark.parametrize("literal", ["%", "_", "/"])
def test_prefix_search_escapes_sql_wildcards(literal: str) -> None:
    async def check(session: AsyncSession) -> None:
        repository = SQLAlchemyUserRepositoryAdapter(session=session)
        prefix = f"repo-{uuid4().hex}"
        expected = new_user(username=prefix + literal + "suffix")
        await repository.create(new_user(username=prefix + "other"))
        await repository.create(expected)
        assert await repository.find_by_username_prefix(
            prefix + literal, limit=10, offset=0,
        ) == (expected,)

    run_check(check)


def test_user_constraints_raise_domain_errors() -> None:
    async def check(session: AsyncSession) -> None:
        repository = SQLAlchemyUserRepositoryAdapter(session=session)
        entity = await repository.create(new_user())
        with pytest.raises(AlreadyExistsException):
            async with session.begin_nested():
                await repository.create(
                    replace(new_user(), email=entity.email),
                )
        with pytest.raises(ConflictException) as error:
            await repository.update(replace(
                entity,
                created_at=entity.created_at - timedelta(seconds=1),
            ))
        assert error.value.details["fields"] == ["created_at"]
        assert await repository.get_by_id(entity.id) == entity

    run_check(check)


def test_credential_rotation_and_current_uniqueness() -> None:
    async def check(session: AsyncSession) -> None:
        users = SQLAlchemyUserRepositoryAdapter(session=session)
        repository = SQLAlchemyCredentialRepositoryAdapter(
            session=session,
        )
        user = await users.create(new_user())
        old = CredentialEntity(
            user_id=user.id, password_hash="old-hash",
            created_at=user.created_at,
        )
        assert await repository.create(old) == old
        assert await repository.get_current_by_user_id(
            user.id, for_update=True,
        ) == old
        retired = replace(old, is_current=False)
        assert await repository.update(retired) == retired
        current = CredentialEntity(
            user_id=user.id, password_hash="new-hash",
            created_at=user.created_at + timedelta(seconds=1),
        )
        assert await repository.create(current) == current
        assert await repository.get_current_by_user_id(
            user.id,
        ) == current
        assert await repository.list_by_user_id(
            user.id, limit=1, offset=0,
        ) == (retired,)
        assert await repository.list_by_user_id(
            user.id, limit=1, offset=1,
        ) == (current,)
        with pytest.raises(AlreadyExistsException):
            async with session.begin_nested():
                await repository.create(replace(current, id=uuid4()))
        with pytest.raises(ConflictException) as error:
            await repository.update(replace(
                current, password_hash="changed-hash",
            ))
        assert error.value.details["fields"] == ["password_hash"]
        assert "new-hash" not in str(error.value.details)
        assert await repository.delete(retired) == retired
        with pytest.raises(NotFoundException):
            await repository.get_by_id(retired.id)

    run_check(check)


def test_session_crud_and_hash_roundtrip() -> None:
    async def check(session: AsyncSession) -> None:
        users = SQLAlchemyUserRepositoryAdapter(session=session)
        repository = SQLAlchemySessionRepositoryAdapter(
            session=session,
        )
        user = await users.create(new_user())
        entity = new_session(user.id)
        assert await repository.create(entity) == entity
        assert await repository.get_by_id(
            entity.id, for_update=True,
        ) == entity
        used = replace(
            entity,
            last_used_at=entity.last_used_at + timedelta(minutes=1),
            expires_at=entity.expires_at + timedelta(minutes=1),
        )
        assert await repository.update(used) == used
        closed = replace(
            used, closed_at=used.last_used_at + timedelta(seconds=1),
        )
        assert await repository.update(closed) == closed
        assert await repository.list_by_user_id(
            user.id, limit=10, offset=0,
        ) == (closed,)
        with pytest.raises(ConflictException) as error:
            await repository.update(replace(
                closed, secret_hash="replacement-hash",
            ))
        assert error.value.details["fields"] == ["secret_hash"]
        assert "private-secret-hash" not in str(error.value.details)
        assert await repository.delete(closed) == closed
        with pytest.raises(NotFoundException):
            await repository.get_by_id(entity.id)

    run_check(check)


def test_session_constraint_errors_are_translated_at_flush() -> None:
    async def check(session: AsyncSession) -> None:
        users = SQLAlchemyUserRepositoryAdapter(session=session)
        user = await users.create(new_user())
        repository = SQLAlchemySessionRepositoryAdapter(
            session=session,
        )
        entity = new_session(user.id)
        with pytest.raises(DataFormatException) as error:
            async with session.begin_nested():
                await repository.create(replace(
                    entity, expires_at=entity.last_used_at,
                ))
        assert error.value.details["sqlstate"] == "23514"
        with pytest.raises(NotFoundException):
            await repository.get_by_id(entity.id)

    run_check(check)


def test_user_delete_cascades_without_loading_relationships() -> None:
    async def check(session: AsyncSession) -> None:
        users = SQLAlchemyUserRepositoryAdapter(session=session)
        credentials = SQLAlchemyCredentialRepositoryAdapter(
            session=session,
        )
        sessions = SQLAlchemySessionRepositoryAdapter(session=session)
        user = await users.create(new_user())
        credential = await credentials.create(CredentialEntity(
            user_id=user.id, password_hash="hash",
            created_at=user.created_at,
        ))
        login_session = await sessions.create(new_session(user.id))
        await users.delete(user)
        with pytest.raises(NotFoundException):
            await credentials.get_by_id(credential.id)
        with pytest.raises(NotFoundException):
            await sessions.get_by_id(login_session.id)
        assert await credentials.list_by_user_id(
            user.id, limit=20, offset=0,
        ) == ()
        assert await sessions.list_by_user_id(
            user.id, limit=20, offset=0,
        ) == ()

    run_check(check)


def test_repositories_flush_without_commit() -> None:
    async def check(session: AsyncSession) -> None:
        users = SQLAlchemyUserRepositoryAdapter(session=session)
        credentials = SQLAlchemyCredentialRepositoryAdapter(
            session=session,
        )
        sessions = SQLAlchemySessionRepositoryAdapter(session=session)
        user = await users.create(new_user())
        credential = await credentials.create(CredentialEntity(
            user_id=user.id, password_hash="hash",
            created_at=user.created_at,
        ))
        login_session = await sessions.create(new_session(user.id))
        assert await users.get_by_id(user.id) == user
        assert DATABASE_URL is not None
        engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
        try:
            async with engine.connect() as other:
                for model, entity_id in (
                    (UserORM, user.id),
                    (CredentialORM, credential.id),
                    (SessionORM, login_session.id),
                ):
                    statement = select(model.id).where(
                        model.id == entity_id,
                    )
                    assert await other.scalar(statement) is None
        finally:
            await engine.dispose()

    run_check(check)


def test_factory_owns_commit_and_rollback() -> None:
    async def run() -> None:
        from sqlalchemy.engine import make_url

        from app.infrastructure.database.session import (
            SessionController,
        )

        assert DATABASE_URL is not None
        url = make_url(DATABASE_URL)
        controller = SessionController(
            postgres_user=url.username or "",
            postgres_password=url.password or "",
            postgres_host=url.host or "",
            postgres_port=url.port or 5432,
            postgres_db=url.database or "",
        )
        saved = new_user()
        rolled_back = new_user()
        try:
            async with controller.session() as session:
                users = SQLAlchemyUserRepositoryAdapter(
                    session=session,
                )
                await users.create(saved)
            async with controller.session() as session:
                users = SQLAlchemyUserRepositoryAdapter(
                    session=session,
                )
                assert await users.get_by_id(saved.id) == saved
            with pytest.raises(ConflictException):
                async with controller.session() as session:
                    users = SQLAlchemyUserRepositoryAdapter(
                        session=session,
                    )
                    credentials = (
                        SQLAlchemyCredentialRepositoryAdapter(
                            session=session,
                        )
                    )
                    sessions = SQLAlchemySessionRepositoryAdapter(
                        session=session,
                    )
                    await users.create(rolled_back)
                    await credentials.create(CredentialEntity(
                        user_id=rolled_back.id,
                        password_hash="rollback-hash",
                        created_at=rolled_back.created_at,
                    ))
                    await sessions.create(new_session(rolled_back.id))
                    raise ConflictException(
                        details={"reason": "rollback_test"},
                    )
            async with controller.session() as session:
                repository = SQLAlchemyUserRepositoryAdapter(
                    session=session,
                )
                with pytest.raises(NotFoundException):
                    await repository.get_by_id(rolled_back.id)
                await repository.delete(saved)
        finally:
            await controller.dispose()

    asyncio.run(run())
