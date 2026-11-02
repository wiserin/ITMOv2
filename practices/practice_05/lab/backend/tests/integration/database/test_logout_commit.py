import asyncio
import os

import logout_support as support
import pytest
from sqlalchemy import select

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="Real migrated PostgreSQL is required",
)


def test_session_failure_logs_are_safe(caplog):
    async def run():
        database = support.controller()
        try:
            with pytest.raises(RuntimeError):
                async with database.session() as session:
                    assert await session.scalar(select(1)) == 1
                    raise RuntimeError("RAW_SQL_secret_cookie")
        finally:
            await database.dispose()

    asyncio.run(run())
    assert "RAW_SQL_secret_cookie" not in caplog.text
    assert "rolled back" not in caplog.text


def test_commit_acknowledgement_log_does_not_claim_rollback(caplog):
    async def run():
        database = support.controller()

        async def lost():
            raise RuntimeError("private_commit_exception")

        from sqlalchemy.ext.asyncio import async_sessionmaker

        database._factory = async_sessionmaker(
            database._engine, class_=support.HookedSession,
            expire_on_commit=False, autoflush=False,
        )
        support.HookedSession.after_commit = staticmethod(lost)
        try:
            with pytest.raises(RuntimeError):
                async with database.session() as session:
                    await session.scalar(select(1))
        finally:
            support.HookedSession.after_commit = None
            await database.dispose()

    asyncio.run(run())
    assert "private_commit_exception" not in caplog.text
    assert "rolled back" not in caplog.text
