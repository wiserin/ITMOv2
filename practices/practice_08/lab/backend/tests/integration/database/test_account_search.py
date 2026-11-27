from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import NonCallableMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.user import UserDTO
from app.application.usecases.auth import AuthUseCase
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.session import SessionController
from app.presentation.api.cookies import SESSION_COOKIE_NAME
from app.presentation.api.di.auth import get_auth_usecase
from app.presentation.api.di.clients.postgres import (
    get_postgres_session,
)
from app.presentation.api.routes import router_v1
from app.presentation.setup_exceptions import setup_exception_handlers

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_DATABASE_URL must point to a migrated PostgreSQL",
)


def test_account_search_uses_repository_and_factory() -> None:
    assert DATABASE_URL is not None
    url = make_url(DATABASE_URL)
    controller = SessionController(
        postgres_user=url.username or "",
        postgres_password=url.password or "",
        postgres_host=url.host or "",
        postgres_port=url.port or 5432,
        postgres_db=url.database or "",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await controller.dispose()

    app = FastAPI(lifespan=lifespan)
    setup_exception_handlers(app)
    app.include_router(router_v1)
    auth = NonCallableMock(spec=AuthUseCase)
    auth.authenticate.return_value = UserDTO(
        id=UUID("899f2a44-9842-4d1a-b951-03bc78d1e6e9"),
        email="root@example.com",
        username="root", role=UserRole.ADMIN, is_active=True,
    )

    async def session_dependency() -> AsyncIterator[AsyncSession]:
        async with controller.session() as session:
            yield session

    overrides = app.dependency_overrides
    overrides[get_postgres_session] = session_dependency
    app.dependency_overrides[get_auth_usecase] = lambda: auth
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set(SESSION_COOKIE_NAME, "test-session-token")
        response = client.get(
            "/v1/account/find/root", params={"limit": 1, "offset": 0},
        )
        assert response.status_code == 200
        assert response.json()["accounts"][0]["username"] == "root"
        assert response.json()["accounts"][0]["role"] == "admin"
        assert len(response.json()["accounts"]) == 1
        empty = client.get(
            "/v1/account/find/root", params={"limit": 1, "offset": 1},
        )
        assert empty.status_code == 200
        assert empty.json() == {"accounts": []}
