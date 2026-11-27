"""Real database harness retaining production finalization."""

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.domain.entities.session import SessionEntity
from app.domain.entities.token import SessionTokenEntity
from app.domain.entities.user import UserEntity
from app.domain.enums.user_role import UserRole
from app.infrastructure.database.models import SessionORM, UserORM
from app.infrastructure.database.repositories.session import (
    SQLAlchemySessionRepositoryAdapter,
)
from app.infrastructure.database.repositories.user import (
    SQLAlchemyUserRepositoryAdapter,
)
from app.infrastructure.database.session import SessionController
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


def controller() -> SessionController:
    url = make_url(os.environ["TEST_DATABASE_URL"])
    result = SessionController(
        postgres_user=url.username,
        postgres_password=url.password,
        postgres_host=url.host,
        postgres_port=url.port or 5432,
        postgres_db=url.database,
    )
    # Connections do not escape a scenario's event loop.
    result._engine = create_async_engine(url, poolclass=NullPool)
    result._factory.configure(bind=result._engine)
    return result


def test_app(database, jwt_provider, secret_manager) -> FastAPI:
    app = FastAPI()
    app.include_router(router_v1)
    setup_exception_handlers(app)

    async def session_dependency():
        async with database.session() as session:
            yield session

    async def auth_dependency():
        async with database.session() as session:
            yield session

    app.dependency_overrides.update({
        get_postgres_session: session_dependency,
        get_auth_postgres_session: auth_dependency,
        get_jwt_provider: lambda: jwt_provider,
        get_secret_manager: lambda: secret_manager,
        get_session_idle_timeout: lambda: 30,
    })
    return app


@dataclass(kw_only=True)
class Seed:
    user: UserEntity
    session: SessionEntity
    token: str


async def seed(
        database, jwt_provider, secret_manager,
        *, role=UserRole.USER, active=True, owner=None) -> Seed:
    now = datetime.now(UTC)
    user = owner or UserEntity(
        email=f"{uuid4()}@example.com", username="logout-fixture",
        created_at=now, updated_at=now, role=role, is_active=active,
    )
    secret = "logout-fixture-secret"
    entity = SessionEntity(
        user_id=user.id,
        secret_hash=await secret_manager.hash_secret(secret),
        created_at=now, last_used_at=now,
        expires_at=now + timedelta(minutes=30),
    )
    async with database.session() as session:
        if owner is None:
            await SQLAlchemyUserRepositoryAdapter(
                session=session,
            ).create(user)
        await SQLAlchemySessionRepositoryAdapter(
            session=session,
        ).create(entity)
    return Seed(
        user=user, session=entity,
        token=jwt_provider.encode(SessionTokenEntity(
            session_id=entity.id, secret=secret, issued_at=now,
        )),
    )


async def snapshot(database, session_id):
    async with database.session() as session:
        row = await session.get(SessionORM, session_id)
        if row is None:
            return None
        return {
            column.name: getattr(row, column.name)
            for column in SessionORM.__table__.columns
        }


async def cleanup(database, *seeds):
    async with database.session() as session:
        await session.execute(delete(UserORM).where(
            UserORM.id.in_([item.user.id for item in seeds]),
        ))
    await database.dispose()


async def ready(database):
    async with database.session() as session:
        return await session.scalar(select(1)) == 1


class Gate:
    def __init__(self):
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def pause(self):
        self.entered.set()
        await asyncio.wait_for(self.release.wait(), timeout=10)


class HookedSession(AsyncSession):
    """Fault/gate hooks around real SQL operations."""

    before_commit: Callable[[], Awaitable[None]] | None = None
    after_commit: Callable[[], Awaitable[None]] | None = None

    async def commit(self):
        if self.before_commit is not None:
            await self.before_commit()
        await super().commit()
        if self.after_commit is not None:
            await self.after_commit()


async def cleanup_email(email):
    database = controller()
    try:
        async with database.session() as session:
            await session.execute(delete(UserORM).where(
                UserORM.email == email,
            ))
    finally:
        await database.dispose()


def create_server_app():
    """Full-stack test API, real adapters and ephemeral key."""
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    from app.infrastructure.security.jwt import (
        EdDSAJwtProviderPortAdapter,
    )
    from app.infrastructure.security.secret import (
        Argon2SecretManagerPortAdapter,
    )

    key = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return test_app(
        controller(),
        EdDSAJwtProviderPortAdapter(
            private_key=base64.b64encode(key).decode(),
        ),
        Argon2SecretManagerPortAdapter(time_cost=1, memory_cost=1024),
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "cleanup-email":
        asyncio.run(cleanup_email(sys.argv[2]))
    else:
        raise SystemExit("Expected cleanup-email TEST_EMAIL")
