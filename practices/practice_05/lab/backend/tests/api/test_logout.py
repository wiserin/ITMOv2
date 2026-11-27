from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.exceptions.entities import (
    AuthenticationException,
    DataFormatException,
    ServiceUnavailableException,
)
from app.presentation.api.di.logout import get_logout_usecase
from app.presentation.api.routes import router_v1
from app.presentation.setup_exceptions import setup_exception_handlers


@pytest.fixture
def logout_client():
    app = FastAPI()
    app.include_router(router_v1)
    setup_exception_handlers(app)
    usecase = AsyncMock()
    app.dependency_overrides[get_logout_usecase] = lambda: usecase
    with TestClient(
        app, base_url="https://testserver",
        raise_server_exceptions=False,
    ) as client:
        yield client, usecase, app


def assert_cookie(response, deleted):
    cookie = response.headers.get("set-cookie", "")
    if not deleted:
        assert "session_token" not in cookie
        return
    for value in [
        "session_token=", "Path=/", "Max-Age=0", "expires=",
        "Secure", "HttpOnly", "SameSite=lax",
    ]:
        assert value.lower() in cookie.lower()
    assert "domain=" not in cookie.lower()


def test_exact_success_and_schema(logout_client):
    client, usecase, app = logout_client
    response = client.post("/v1/auth/logout", headers={
        "X-AnimeMap-Logout": "1", "Cookie": "session_token=jwt",
        "Content-Type": "application/json",
    })
    assert response.status_code == 204
    assert response.content == b""
    assert "location" not in response.headers
    assert response.headers["cache-control"] == "no-store"
    assert_cookie(response, True)
    usecase.logout.assert_awaited_once_with("jwt")
    schema = app.openapi()["paths"]["/v1/auth/logout"]["post"]
    assert "requestBody" not in schema
    assert "content" not in schema["responses"]["204"]
    assert schema["operationId"] == "auth_logout"
    assert schema["security"]


@pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS", "PUT"])
def test_unsupported_methods(logout_client, method):
    client, usecase, _ = logout_client
    response = client.request(method, "/v1/auth/logout")
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"
    assert response.headers["cache-control"] == "no-store"
    if method == "HEAD":
        assert response.content == b""
    else:
        assert response.json()["error"] == "method_not_allowed"
    assert_cookie(response, False)
    usecase.logout.assert_not_awaited()


@pytest.mark.parametrize("headers", [
    [], [("X-AnimeMap-Logout", "0")],
    [("X-AnimeMap-Logout", "1"), ("x-animemap-logout", "1")],
])
def test_csrf_before_body_query_cookie(logout_client, headers):
    client, usecase, _ = logout_client
    response = client.post(
        "/v1/auth/logout?x=", content=b"{bad", headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["details"]["reason"] == "csrf_check_failed"
    assert_cookie(response, False)
    usecase.logout.assert_not_awaited()


@pytest.mark.parametrize("body,query", [
    (b"{}", ""), (b"null", ""), (b" ", ""), (b"{bad", ""),
    (b"", "?x="),
])
def test_input_before_cookie(logout_client, body, query):
    client, usecase, _ = logout_client
    response = client.post(
        "/v1/auth/logout" + query, content=body,
        headers={"X-AnimeMap-Logout": "1"},
    )
    assert response.status_code == 400
    assert_cookie(response, False)
    usecase.logout.assert_not_awaited()


@pytest.mark.parametrize("exception,status", [
    (AuthenticationException(details={
        "reason": "invalid_token",
    }), 401),
    (DataFormatException(details={"field": "secret_hash"}), 400),
    (ServiceUnavailableException(), 503),
    (RuntimeError("private secret SQL"), 500),
])
def test_actual_error_response(logout_client, exception, status):
    client, usecase, _ = logout_client
    usecase.logout.side_effect = exception
    response = client.post("/v1/auth/logout", headers={
        "X-AnimeMap-Logout": "1", "Cookie": "session_token=jwt",
    })
    assert response.status_code == status
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert isinstance(data["error"], str)
    assert isinstance(data["message"], str)
    assert isinstance(data["details"], dict)
    assert "private secret SQL" not in response.text
    assert_cookie(response, status == 401)
