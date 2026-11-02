import asyncio
import os
from dataclasses import replace

import logout_support as support
import pytest
from fastapi.testclient import TestClient

from app.domain.enums.user_role import UserRole
from app.infrastructure.database.repositories.user import (
    SQLAlchemyUserRepositoryAdapter,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="Real migrated PostgreSQL is required",
)


@pytest.mark.parametrize("role", list(UserRole))
@pytest.mark.parametrize("active", [True, False])
def test_persisted_close_only_presented_session(
        jwt_provider, secret_manager, role, active):
    database = support.controller()

    async def setup():
        target = await support.seed(
            database, jwt_provider, secret_manager,
            role=role, active=active,
        )
        return target, await support.seed(
                database, jwt_provider, secret_manager,
                owner=target.user,
        )

    target, independent = asyncio.run(setup())
    before = asyncio.run(support.snapshot(
        database, target.session.id,
    ))
    other = asyncio.run(support.snapshot(
        database, independent.session.id,
    ))
    try:
        app = support.test_app(database, jwt_provider, secret_manager)
        with TestClient(app, base_url="https://testserver") as client:
            response = client.post("/v1/auth/logout", headers={
                "X-AnimeMap-Logout": "1",
                "Cookie": f"session_token={target.token}",
            })
            assert response.status_code == 204
            assert response.content == b""
            after = asyncio.run(support.snapshot(
                database, target.session.id,
            ))
            assert after["closed_at"] >= before["last_used_at"]
            assert after | {"closed_at": None} == before
            assert asyncio.run(support.snapshot(
                database, independent.session.id,
            )) == other

            async def reactivate():
                async with database.session() as session:
                    repo = SQLAlchemyUserRepositoryAdapter(
                        session=session,
                    )
                    user = await repo.get_by_id(target.user.id)
                    assert user == target.user
                    await repo.update(replace(user, is_active=True))

            asyncio.run(reactivate())
            assert client.get("/v1/account/me", headers={
                "Cookie": f"session_token={target.token}",
            }).status_code == 401
            assert client.get("/v1/account/me", headers={
                "Cookie": f"session_token={independent.token}",
            }).status_code == 200
    finally:
        asyncio.run(support.cleanup(database, target, independent))
