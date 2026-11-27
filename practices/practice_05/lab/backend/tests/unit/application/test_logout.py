import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import NonCallableMock
from uuid import uuid4

import pytest

from app.application.usecases.logout import LogoutUseCase
from app.domain.entities.session import SessionEntity
from app.domain.entities.token import SessionTokenEntity
from app.domain.entities.user import UserEntity
from app.domain.enums.user_role import UserRole
from app.domain.exceptions.entities import AuthenticationException
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


@pytest.mark.parametrize("role", list(UserRole))
@pytest.mark.parametrize("active", [True, False])
def test_close_without_auth_renewal(
        jwt_provider, secret_manager, role, active):
    async def run():
        now = datetime.now(UTC)
        user = UserEntity(
            email="logout@example.com", username="logout",
            created_at=now, updated_at=now, role=role,
            is_active=active,
        )
        entity = SessionEntity(
            user_id=user.id,
            secret_hash=await secret_manager.hash_secret("secret"),
            created_at=now, last_used_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        calls = []
        users = NonCallableMock(spec=UserRepository)
        sessions = NonCallableMock(spec=SessionRepository)

        async def get_user(*args, **kwargs):
            calls.append("user-lock")
            assert kwargs["for_update"] is True
            return user

        async def get_session(*args, **kwargs):
            calls.append("lock" if kwargs else "read")
            return entity

        users.get_by_id.side_effect = get_user
        sessions.get_by_id.side_effect = get_session
        usecase = LogoutUseCase(
            user_repository=users, session_repository=sessions,
            jwt_provider=jwt_provider, secret_manager=secret_manager,
        )
        await usecase.logout(jwt_provider.encode(SessionTokenEntity(
            session_id=entity.id, secret="secret", issued_at=now,
        )))
        assert calls == ["read", "user-lock", "lock"]
        closed = sessions.update.call_args.args[0]
        assert closed.closed_at >= entity.last_used_at
        assert replace(closed, closed_at=None) == entity

    asyncio.run(run())


@pytest.mark.parametrize("mutation", [
    "owner", "hash", "closed", "expiry",
])
def test_rechecks_verified_snapshot(
        jwt_provider, secret_manager, mutation):
    async def run():
        now = datetime.now(UTC)
        user = UserEntity(
            email="logout@example.com", username="logout",
            created_at=now, updated_at=now,
        )
        entity = SessionEntity(
            user_id=user.id,
            secret_hash=await secret_manager.hash_secret("secret"),
            created_at=now, last_used_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        changes = {
            "owner": {"user_id": uuid4()},
            "hash": {"secret_hash": "different"},
            "closed": {"closed_at": now},
            "expiry": {"expires_at": now},
        }
        users = NonCallableMock(spec=UserRepository)
        users.get_by_id.return_value = user
        sessions = NonCallableMock(spec=SessionRepository)
        sessions.get_by_id.side_effect = [
            entity, replace(entity, **changes[mutation]),
        ]
        usecase = LogoutUseCase(
            user_repository=users, session_repository=sessions,
            jwt_provider=jwt_provider, secret_manager=secret_manager,
        )
        with pytest.raises(AuthenticationException):
            await usecase.logout(jwt_provider.encode(
                SessionTokenEntity(
                    session_id=entity.id, secret="secret",
                    issued_at=now,
                ),
            ))
        sessions.update.assert_not_awaited()

    asyncio.run(run())
