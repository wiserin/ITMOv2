from __future__ import annotations

from http.cookies import SimpleCookie
from unittest.mock import NonCallableMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.login import LoginDTO
from app.domain.exceptions.entities import AuthenticationException
from app.presentation.api.cookies import SESSION_COOKIE_NAME
from app.presentation.api.di.clients.postgres import (
    get_postgres_session,
)
from app.presentation.api.routes import router_v1
from app.presentation.api.schemas.responses.login import LoginResponse
from app.presentation.setup_exceptions import setup_exception_handlers


def test_login_sets_secure_httponly_session_cookie(
        client: TestClient,
        login_use_case: NonCallableMock,
        register_use_case: NonCallableMock) -> None:
    response = client.post("/v1/auth/login", json={
        "email": " ROOT@EXAMPLE.COM ", "password": " root ",
    })
    assert response.status_code == 200
    assert response.json() == {}
    assert response.headers["cache-control"] == "no-store"
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    session_cookie = cookie[SESSION_COOKIE_NAME]
    assert session_cookie.value == "session.jwt.token"
    assert session_cookie["secure"]
    assert session_cookie["httponly"]
    assert session_cookie["samesite"] == "lax"
    assert session_cookie["path"] == "/"
    assert not session_cookie["expires"]
    assert not session_cookie["max-age"]
    assert "session.jwt.token" not in response.text
    login_use_case.login.assert_awaited_once()
    data = login_use_case.login.call_args.args[0]
    assert isinstance(data, LoginDTO)
    assert data.email == "root@example.com"
    assert data.password == " root "
    assert " root " not in repr(data)
    register_use_case.register.assert_not_awaited()


@pytest.mark.parametrize("payload", [
    {"email": "root@example.com"},
    {"email": "not-an-email", "password": "root"},
    {"email": "x" * 250 + "@example.com", "password": "root"},
    {"email": "root@example.com", "password": ""},
    {"email": "root@example.com", "password": 1234},
    {
        "email": "root@example.com",
        "password": "root", "role": "admin",
    },
    {"email": "root@animemap.local", "password": "root"},
])
def test_invalid_login_is_rejected_before_use_case(
        client: TestClient,
        login_use_case: NonCallableMock,
        payload: dict[str, object]) -> None:
    response = client.post("/v1/auth/login", json=payload)
    assert response.status_code == 400
    login_use_case.login.assert_not_awaited()
    assert "set-cookie" not in response.headers


def test_bad_credentials_response(
        client: TestClient,
        login_use_case: NonCallableMock) -> None:
    login_use_case.login.side_effect = AuthenticationException(
        details={"reason": "invalid_credentials"},
    )
    response = client.post("/v1/auth/login", json={
        "email": "root@example.com", "password": "wrong-password",
    })
    assert response.status_code == 401
    assert response.json() == {
        "error": "authentication_failed",
        "message": "Authentication failed",
        "details": {"reason": "invalid_credentials"},
    }
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("payload", [
    '{"token": "private-jwt"}',
    '{"expires_at": "2026-10-29T00:00:00Z"}',
])
def test_login_response_excludes_token_and_session_expiration(
        payload: str) -> None:
    with pytest.raises(ValidationError):
        LoginResponse.model_validate_json(payload)


@pytest.mark.parametrize("path, payload", [
    ("/v1/auth/login", {
        "email": "root@example.com", "password": "root",
    }),
    ("/v1/auth/register", {
        "email": "new@example.com",
        "username": "new", "password": "password",
    }),
])
def test_unconfigured_use_case_does_not_report_success(
        path: str,
        payload: dict[str, str]) -> None:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(router_v1)
    session = NonCallableMock(spec=AsyncSession)
    app.dependency_overrides[get_postgres_session] = lambda: session
    with TestClient(app, follow_redirects=False) as client:
        response = client.post(path, json=payload)
    assert response.status_code == 501
    assert "location" not in response.headers
