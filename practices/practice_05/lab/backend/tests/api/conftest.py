from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import NonCallableMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.dto.login import LoginResultDTO
from app.application.dto.user import UserDTO
from app.application.usecases.auth import AuthUseCase
from app.application.usecases.login import LoginUseCase
from app.application.usecases.register import RegisterUseCase
from app.presentation.api.di.auth import AuthUseCaseDI, get_auth_usecase
from app.presentation.api.di.login import get_login_usecase
from app.presentation.api.di.register import get_register_usecase
from app.presentation.api.routes import router_v1


@pytest.fixture
def login_use_case() -> NonCallableMock:
    use_case = NonCallableMock(spec=LoginUseCase)
    use_case.login.return_value = LoginResultDTO(token="session.jwt.token")
    return use_case


@pytest.fixture
def register_use_case() -> NonCallableMock:
    use_case = NonCallableMock(spec=RegisterUseCase)
    use_case.register.return_value = None
    return use_case


@pytest.fixture
def auth_use_case() -> NonCallableMock:
    use_case = NonCallableMock(spec=AuthUseCase)
    use_case.authenticate.return_value = UserDTO(
        id=UUID("899f2a44-9842-4d1a-b951-03bc78d1e6e9"), email="root@example.com",
        username="root", role=3, is_active=True,
    )
    return use_case


@pytest.fixture
def client(
        login_use_case: NonCallableMock,
        register_use_case: NonCallableMock,
        auth_use_case: NonCallableMock) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router_v1)
    app.dependency_overrides[get_login_usecase] = lambda: login_use_case
    app.dependency_overrides[get_register_usecase] = lambda: register_use_case
    app.dependency_overrides[get_auth_usecase] = lambda: auth_use_case

    @app.get("/private")
    async def private(user: AuthUseCaseDI) -> dict[str, str]:
        return {"user_id": str(user.id)}

    with TestClient(app, base_url="https://testserver", follow_redirects=False) as test_client:
        yield test_client
