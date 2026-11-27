from collections.abc import AsyncIterator
from unittest.mock import NonCallableMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.exceptions.entities import ConflictException
from app.infrastructure.database.repositories.credential import (
    SQLAlchemyCredentialRepositoryAdapter,
)
from app.infrastructure.database.repositories.session import (
    SQLAlchemySessionRepositoryAdapter,
)
from app.infrastructure.database.repositories.user import (
    SQLAlchemyUserRepositoryAdapter,
)
from app.presentation.api.di.clients.postgres import (
    get_postgres_session,
)
from app.presentation.api.di.repositories.credential import (
    CredentialRepositoryDI,
)
from app.presentation.api.di.repositories.session import (
    SessionRepositoryDI,
)
from app.presentation.api.di.repositories.user import UserRepositoryDI
from app.presentation.setup_exceptions import setup_exception_handlers


def test_repositories_share_session_with_function_cleanup() -> None:
    app = FastAPI()
    events: list[str] = []
    session = NonCallableMock(spec=AsyncSession)

    async def session_dependency() -> AsyncIterator[AsyncSession]:
        events.append("open")
        try:
            yield session
        finally:
            events.append("close")

    overrides = app.dependency_overrides
    overrides[get_postgres_session] = session_dependency

    @app.get("/wiring")
    async def wiring(
            users: UserRepositoryDI,
            credentials: CredentialRepositoryDI,
            sessions: SessionRepositoryDI) -> dict[str, bool]:
        assert isinstance(users, SQLAlchemyUserRepositoryAdapter)
        assert isinstance(
            credentials, SQLAlchemyCredentialRepositoryAdapter,
        )
        assert isinstance(
            sessions, SQLAlchemySessionRepositoryAdapter,
        )
        return {"shared": (
            users._session is credentials._session
            is sessions._session is session
        )}

    with TestClient(app) as client:
        response = client.get("/wiring")
        assert events == ["open", "close"]
    assert response.status_code == 200
    assert response.json() == {"shared": True}


def test_finalization_error_is_mapped_before_response() -> None:
    app = FastAPI()
    setup_exception_handlers(app)
    session = NonCallableMock(spec=AsyncSession)

    async def failing_session() -> AsyncIterator[AsyncSession]:
        yield session
        raise ConflictException(details={"operation": "commit"})

    overrides = app.dependency_overrides
    overrides[get_postgres_session] = failing_session

    @app.get("/finalization")
    async def finalization(
            users: UserRepositoryDI) -> dict[str, bool]:
        return {"success": True}

    with TestClient(app) as client:
        response = client.get("/finalization")
    assert response.status_code == 409
    assert response.json()["details"] == {"operation": "commit"}
    assert "success" not in response.json()
