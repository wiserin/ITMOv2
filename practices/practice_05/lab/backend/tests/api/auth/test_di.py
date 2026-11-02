from __future__ import annotations

from unittest.mock import NonCallableMock

import pytest
from fastapi.testclient import TestClient

from app.application.usecases.login import LoginUseCase
from app.application.usecases.register import RegisterUseCase
from app.domain.exceptions.entities import AuthenticationException
from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.domain.repositories.credential import CredentialRepository
from app.domain.repositories.session import SessionRepository
from app.domain.repositories.user import UserRepository
from app.presentation.api.cookies import SESSION_COOKIE_NAME
from app.presentation.api.di.login import get_login_usecase
from app.presentation.api.di.register import get_register_usecase


def test_normal_di_returns_use_case_without_executing_it(
        jwt_provider: JwtProviderPort,
        secret_manager: SecretManagerPort) -> None:
    users = NonCallableMock(spec=UserRepository)
    credentials = NonCallableMock(spec=CredentialRepository)
    sessions = NonCallableMock(spec=SessionRepository)
    login_use_case = get_login_usecase(
        user_repository=users,
        credential_repository=credentials,
        session_repository=sessions,
        jwt_provider=jwt_provider,
        secret_manager=secret_manager,
        idle_timeout=30,
    )
    register_use_case = get_register_usecase(
        user_repository=users, credentials=credentials,
        secret_manager=secret_manager,
    )
    assert isinstance(login_use_case, LoginUseCase)
    assert isinstance(register_use_case, RegisterUseCase)
    assert not callable(login_use_case)
    assert not callable(register_use_case)
    assert login_use_case._user_repository is users
    assert login_use_case._credential_repository is credentials
    assert login_use_case._session_repository is sessions
    assert register_use_case._user_repository is users
    assert register_use_case._credential_repository is credentials


def test_cookie_is_sent_automatically_and_auth_di_returns_user(
        client: TestClient,
        auth_use_case: NonCallableMock) -> None:
    client.post("/v1/auth/login", json={
        "email": "root@example.com", "password": "root",
    })
    response = client.get("/private")
    assert response.status_code == 200
    user = auth_use_case.authenticate.return_value
    assert response.json() == {"user_id": str(user.id)}
    auth_use_case.authenticate.assert_awaited_once_with(
        "session.jwt.token",
    )


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Bearer header-token"},
])
def test_auth_di_requires_cookie(
        client: TestClient,
        auth_use_case: NonCallableMock,
        headers: dict[str, str]) -> None:
    response = client.get("/private", headers=headers)
    assert response.status_code == 401
    auth_use_case.authenticate.assert_not_awaited()


def test_secure_cookie_is_not_sent_over_http(
        client: TestClient,
        auth_use_case: NonCallableMock) -> None:
    client.post("/v1/auth/login", json={
        "email": "root@example.com", "password": "root",
    })
    response = client.get("http://testserver/private")
    assert response.status_code == 401
    auth_use_case.authenticate.assert_not_awaited()


def test_auth_failure_is_not_a_user(
        client: TestClient,
        auth_use_case: NonCallableMock) -> None:
    auth_use_case.authenticate.side_effect = AuthenticationException(
        details={"reason": "session_expired"},
    )
    client.cookies.set(SESSION_COOKIE_NAME, "expired-session")
    response = client.get("/private")
    assert response.status_code == 401
    assert response.json() == {
        "error": "authentication_failed",
        "message": "Authentication failed",
        "details": {"reason": "session_expired"},
    }


def test_openapi_uses_cookie_security(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    schemes = schema["components"]["securitySchemes"]
    assert schemes["SessionCookie"] == {
        "type": "apiKey", "in": "cookie", "name": SESSION_COOKIE_NAME,
    }
    assert schema["paths"]["/private"]["get"]["security"] == [
        {"SessionCookie": []},
    ]
