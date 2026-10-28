import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, NonCallableMock

import pytest
from argon2 import PasswordHasher

from app.application.usecases.auth import AuthUseCase
from app.domain.entities.session import SessionEntity
from app.domain.entities.token import SessionTokenEntity
from app.domain.entities.user import UserEntity
from app.domain.exceptions.entities import AuthenticationException
from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository


@pytest.mark.parametrize("state", ["closed", "expired", "inactive"])
def test_recheck_after_verify_prevents_session_revival(
        jwt_provider: JwtProviderPort,
        secret_manager: SecretManagerPort,
        state: str) -> None:
    async def scenario() -> None:
        now = datetime.now(UTC)
        user = UserEntity(
            email="fan@example.com", username="fan",
            created_at=now, updated_at=now,
        )
        session = SessionEntity(
            user_id=user.id,
            secret_hash=await secret_manager.hash_secret("secret"),
            created_at=now, last_used_at=now,
            expires_at=now + timedelta(minutes=30),
        )
        latest = session
        if state == "closed":
            latest = replace(session, closed_at=now)
        elif state == "expired":
            latest = replace(session, expires_at=now)
        else:
            user = replace(user, is_active=False)
        users = NonCallableMock(spec=UserRepository)
        users.get_by_id.return_value = user
        sessions = NonCallableMock(spec=SessionRepository)
        sessions.get_by_id.side_effect = [session, latest]
        commit = AsyncMock()
        use_case = AuthUseCase(
            user_repository=users, session_repository=sessions,
            jwt_provider=jwt_provider, secret_manager=secret_manager,
            session_idle_timeout_minutes=30, commit=commit,
        )
        token = jwt_provider.encode(SessionTokenEntity(
            session_id=session.id, secret="secret", issued_at=now,
        ))
        with pytest.raises(AuthenticationException):
            await use_case.authenticate(token)
        sessions.update.assert_not_awaited()
        commit.assert_not_awaited()

    asyncio.run(scenario())


@pytest.mark.parametrize("method", ["hash", "verify"])
def test_argon2_runs_outside_event_loop(
        secret_manager: SecretManagerPort,
        monkeypatch: pytest.MonkeyPatch,
        method: str) -> None:
    import threading

    main_thread = threading.get_ident()
    calls: list[int] = []
    original = getattr(secret_manager._hasher, method)

    def operation(
            self: PasswordHasher,
            *args: str) -> str | bool:
        calls.append(threading.get_ident())
        return original(*args)

    monkeypatch.setattr(PasswordHasher, method, operation)

    async def scenario() -> None:
        hashed = await secret_manager.hash_secret("password")
        await secret_manager.verify_secret("password", hashed)

    asyncio.run(scenario())
    assert calls and all(thread != main_thread for thread in calls)
