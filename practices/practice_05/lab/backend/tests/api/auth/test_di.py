from __future__ import annotations

from unittest.mock import NonCallableMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.application.usecases.login import LoginUseCase
from app.application.usecases.register import RegisterUseCase
from app.presentation.api.cookies import SESSION_COOKIE_NAME
from app.presentation.api.di.login import get_login_usecase
from app.presentation.api.di.register import get_register_usecase


def test_normal_di_returns_use_case_without_executing_it() -> None:
    login_use_case = get_login_usecase()
    register_use_case = get_register_usecase()
    assert isinstance(login_use_case, LoginUseCase)
    assert isinstance(register_use_case, RegisterUseCase)
    assert not callable(login_use_case)
    assert not callable(register_use_case)


def test_cookie_is_sent_automatically_and_auth_di_returns_user(
        client: TestClient,
        auth_use_case: NonCallableMock) -> None:
    client.post("/v1/auth/login", json={"email": "root@example.com", "password": "root"})
    response = client.get("/private")
    assert response.status_code == 200
    assert response.json() == {"user_id": str(auth_use_case.authenticate.return_value.id)}
    auth_use_case.authenticate.assert_awaited_once_with("session.jwt.token")


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer header-token"}])
def test_auth_di_requires_cookie(
        client: TestClient,
        auth_use_case: NonCallableMock,
        headers: dict[str, str]) -> None:
    response = client.get("/private", headers=headers)
    assert response.status_code == 401
    auth_use_case.authenticate.assert_not_awaited()


def test_secure_cookie_is_not_sent_over_http(client: TestClient, auth_use_case: NonCallableMock) -> None:
    client.post("/v1/auth/login", json={"email": "root@example.com", "password": "root"})
    response = client.get("http://testserver/private")
    assert response.status_code == 401
    auth_use_case.authenticate.assert_not_awaited()


def test_auth_failure_is_not_a_user(client: TestClient, auth_use_case: NonCallableMock) -> None:
    auth_use_case.authenticate.side_effect = HTTPException(status_code=401, detail="Session expired")
    client.cookies.set(SESSION_COOKIE_NAME, "expired-session")
    response = client.get("/private")
    assert response.status_code == 401
    assert response.json() == {"detail": "Session expired"}


def test_openapi_uses_cookie_security(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["SessionCookie"] == {
        "type": "apiKey", "in": "cookie", "name": SESSION_COOKIE_NAME,
    }
    assert schema["paths"]["/private"]["get"]["security"] == [{"SessionCookie": []}]
