from dataclasses import fields
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.entities.session import SessionEntity
from app.domain.exceptions.entities import AuthenticationException


@pytest.mark.parametrize("shift", [-60, 0, 60])
def test_close_preserves_history_and_clock_invariant(shift):
    now = datetime.now(UTC)
    original = SessionEntity(
        user_id=uuid4(), secret_hash="hash", created_at=now,
        last_used_at=now, expires_at=now + timedelta(hours=1),
    )
    closed = original.close(now=now + timedelta(seconds=shift))
    assert original.closed_at is None
    assert closed.closed_at == max(
        now, now + timedelta(seconds=shift),
    )
    assert closed.close(now=now + timedelta(days=1)) == closed
    for field in fields(original):
        if field.name != "closed_at":
            assert getattr(closed, field.name) == getattr(
                original, field.name,
            )
    assert original.close().closed_at.tzinfo is UTC


@pytest.mark.parametrize("offset", [0, 1])
def test_expiry_equality_is_unusable(offset):
    now = datetime.now(UTC)
    entity = SessionEntity(
        user_id=uuid4(), secret_hash="hash", created_at=now,
        last_used_at=now, expires_at=now,
    )
    with pytest.raises(AuthenticationException) as error:
        entity.ensure_usable(now=now + timedelta(seconds=offset))
    assert error.value.details["reason"] == "session_expired"
