import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.infrastructure.database.models import (
    CredentialORM,
    SessionORM,
    UserORM,
)
from app.presentation.api.di.clients.auth_postgres import (
    get_auth_postgres_session,
)
from app.presentation.api.di.clients.postgres import (
    get_postgres_session,
)
from app.presentation.api.di.ports.jwt import get_jwt_provider
from app.presentation.api.di.ports.secret import get_secret_manager
from app.presentation.api.di.ports.session_timeout import (
    get_session_idle_timeout,
)
from app.presentation.api.routes import router_v1
from app.presentation.setup_exceptions import setup_exception_handlers

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_DATABASE_URL must point to a migrated PostgreSQL",
)


@pytest.fixture
def auth_client(
        jwt_provider: JwtProviderPort,
        secret_manager: SecretManagerPort) -> Iterator[TestClient]:
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def session_dependency() -> AsyncIterator[AsyncSession]:
        async with factory() as session, session.begin():
            yield session

    async def auth_dependency() -> AsyncIterator[AsyncSession]:
        async for session in session_dependency():
            yield session

    app = FastAPI()
    app.include_router(router_v1)
    setup_exception_handlers(app)
    overrides = app.dependency_overrides
    overrides[get_postgres_session] = session_dependency
    overrides[get_auth_postgres_session] = auth_dependency
    overrides[get_jwt_provider] = lambda: jwt_provider
    overrides[get_secret_manager] = lambda: secret_manager
    overrides[get_session_idle_timeout] = lambda: 30
    with TestClient(
        app, base_url="https://testserver", follow_redirects=False,
    ) as client:
        yield client
    asyncio.run(engine.dispose())


def test_full_auth_flow_and_independent_renewal(
        auth_client: TestClient,
        jwt_provider: JwtProviderPort) -> None:
    email = f"{uuid4()}@example.com"
    payload = {
        "email": email, "username": " auth-fan ",
        "password": " password with spaces ",
    }
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def inspect() -> tuple[str, datetime]:
        async with factory() as session:
            user = (await session.scalars(
                select(UserORM).where(UserORM.email == email),
            )).one()
            credential = (await session.scalars(
                select(CredentialORM)
                .where(CredentialORM.user_id == user.id),
            )).one()
            active = (await session.scalars(
                select(SessionORM)
                .where(SessionORM.user_id == user.id),
            )).one()
            assert user.role == 1
            assert user.username == "auth-fan"
            assert credential.password_hash.startswith("$argon2id$")
            assert active.secret_hash.startswith("$argon2id$")
            return active.secret, active.expires_at

    async def cleanup() -> None:
        async with factory.begin() as session:
            await session.execute(
                delete(UserORM).where(UserORM.email == email),
            )
        await engine.dispose()

    try:
        response = auth_client.post("/v1/auth/register", json=payload)
        assert response.status_code == 303
        assert response.headers["location"].endswith("/v1/auth/login")
        assert not auth_client.cookies
        assert auth_client.post(
            "/v1/auth/register", json=payload,
        ).status_code == 409
        assert auth_client.post("/v1/auth/login", json={
            "email": email, "password": "password with spaces",
        }).status_code == 401
        response = auth_client.post("/v1/auth/login", json=payload | {
            "username": "unused",
        })
        assert response.status_code == 400
        response = auth_client.post("/v1/auth/login", json={
            "email": email, "password": payload["password"],
        })
        assert response.status_code == 200
        assert response.json() == {}
        token = auth_client.cookies["session_token"]
        secret, expires_before = asyncio.run(inspect())
        assert jwt_provider.decode(token).secret == secret
        response = auth_client.get("/v1/account/me")
        assert response.status_code == 200
        assert response.json()["role"] == "user"
        assert response.json()["email"] == email
        _, expires_before = asyncio.run(inspect())
        assert auth_client.get(
            "/v1/account/find/auth",
        ).status_code == 403
        _, expires_after = asyncio.run(inspect())
        assert expires_after > expires_before
        assert auth_client.cookies["session_token"] == token
        auth_client.cookies.set("session_token", "broken")
        assert auth_client.get("/v1/account/me").status_code == 401
    finally:
        asyncio.run(cleanup())
