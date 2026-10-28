from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.session import SessionEntity
from app.domain.exceptions.entities import (
    AuthenticationException,
    DataFormatException,
)


@pytest.fixture
def session() -> SessionEntity:
    now = datetime(2026, 10, 29, tzinfo=UTC)
    return SessionEntity(
        user_id=uuid4(), secret="secret", secret_hash="hash",
        created_at=now, last_used_at=now,
        expires_at=now + timedelta(minutes=30),
    )


def test_use_returns_new_session_preserving_identity_and_secrets(
        session: SessionEntity) -> None:
    now = session.created_at + timedelta(minutes=5)
    used = session.use(idle_timeout=timedelta(minutes=20), now=now)
    assert used is not session
    assert used.last_used_at == now
    assert used.expires_at == now + timedelta(minutes=20)
    assert replace(
        used, last_used_at=session.last_used_at,
        expires_at=session.expires_at,
    ) == session
    assert session.last_used_at == session.created_at


@pytest.mark.parametrize("state", ["closed", "expired", "at_expiry"])
def test_use_rejects_unusable_session(
        session: SessionEntity,
        state: str) -> None:
    now = session.created_at + timedelta(minutes=1)
    if state == "closed":
        session = replace(session, closed_at=session.created_at)
    elif state == "expired":
        now = session.expires_at + timedelta(seconds=1)
    else:
        now = session.expires_at
    with pytest.raises(AuthenticationException):
        session.use(idle_timeout=timedelta(minutes=30), now=now)


def test_use_never_moves_last_used_backwards(
        session: SessionEntity) -> None:
    latest = session.created_at + timedelta(minutes=5)
    session = replace(session, last_used_at=latest)
    used = session.use(
        idle_timeout=timedelta(minutes=30),
        now=latest - timedelta(seconds=1),
    )
    assert used.last_used_at == latest
    assert used.expires_at == latest + timedelta(minutes=30)


@pytest.mark.parametrize("minutes", [0, -1])
def test_use_rejects_nonpositive_timeout(
        session: SessionEntity,
        minutes: int) -> None:
    with pytest.raises(DataFormatException):
        session.use(
            idle_timeout=timedelta(minutes=minutes),
            now=session.created_at,
        )
