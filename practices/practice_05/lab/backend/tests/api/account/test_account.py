from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import NonCallableMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities.user import UserEntity
from app.domain.enums.user_role import UserRole
from app.domain.exceptions.entities import AuthenticationException
from app.presentation.api.cookies import SESSION_COOKIE_NAME
from app.presentation.api.di.auth import get_auth_usecase
from app.presentation.api.routes import router_v1
from app.presentation.setup_exceptions import setup_exception_handlers


@pytest.mark.parametrize("role", list(UserRole))
def test_me_returns_current_account_for_every_role(
        client: TestClient,
        auth_use_case: NonCallableMock,
        role: UserRole) -> None:
    user = replace(auth_use_case.authenticate.return_value, role=role)
    auth_use_case.authenticate.return_value = user
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get("/v1/account/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": str(user.id), "email": user.email, "username": user.username,
        "display_name": user.display_name, "role": role.to_string(), "is_active": True,
    }
    assert response.headers["cache-control"] == "no-store"
    auth_use_case.authenticate.assert_awaited_once_with("session-token")


@pytest.mark.parametrize("role", [UserRole.MODERATOR, UserRole.ADMIN])
def test_moderator_and_admin_can_find_accounts_with_duplicate_usernames(
        client: TestClient,
        auth_use_case: NonCallableMock,
        user_repository: NonCallableMock,
        role: UserRole) -> None:
    auth_use_case.authenticate.return_value = replace(
        auth_use_case.authenticate.return_value, role=role,
    )
    now = datetime.now(UTC)
    accounts = tuple(
        UserEntity(
            id=uuid4(), email=f"alice{number}@example.com", username="alice",
            display_name=None, role=UserRole.USER, is_active=True,
            created_at=now, updated_at=now,
        )
        for number in range(2)
    )
    user_repository.find_by_username_prefix.return_value = accounts
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get("/v1/account/find/ali")
    assert response.status_code == 200
    result = response.json()["accounts"]
    assert [account["id"] for account in result] == [str(account.id) for account in accounts]
    assert all(account["role"] == "user" for account in result)
    assert response.headers["cache-control"] == "no-store"
    user_repository.find_by_username_prefix.assert_awaited_once_with("ali", limit=20, offset=0)


def test_regular_user_is_denied_before_search(
        client: TestClient,
        auth_use_case: NonCallableMock,
        user_repository: NonCallableMock) -> None:
    auth_use_case.authenticate.return_value = replace(
        auth_use_case.authenticate.return_value, role=UserRole.USER,
    )
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get("/v1/account/find/ali")
    assert response.status_code == 403
    user_repository.find_by_username_prefix.assert_not_awaited()


@pytest.mark.parametrize("path", ["/v1/account/me", "/v1/account/find/ali"])
def test_account_endpoints_require_cookie(
        client: TestClient,
        auth_use_case: NonCallableMock,
        user_repository: NonCallableMock,
        path: str) -> None:
    response = client.get(path, headers={"Authorization": "Bearer header-token"})
    assert response.status_code == 401
    auth_use_case.authenticate.assert_not_awaited()
    user_repository.find_by_username_prefix.assert_not_awaited()


@pytest.mark.parametrize("path", ["/v1/account/me", "/v1/account/find/ali"])
def test_inactive_accounts_are_not_authenticated(
        client: TestClient,
        auth_use_case: NonCallableMock,
        user_repository: NonCallableMock,
        path: str) -> None:
    auth_use_case.authenticate.return_value = replace(
        auth_use_case.authenticate.return_value, is_active=False,
    )
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    assert client.get(path).status_code == 401
    user_repository.find_by_username_prefix.assert_not_awaited()


@pytest.mark.parametrize("prefix", ["%20%20", "x" * 101])
def test_invalid_prefix_is_not_sent_to_search(
        client: TestClient,
        user_repository: NonCallableMock,
        prefix: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get(f"/v1/account/find/{prefix}")
    assert response.status_code == 400
    user_repository.find_by_username_prefix.assert_not_awaited()


@pytest.mark.parametrize("encoded, expected", [("%20Ali%20", "Ali"), ("%25", "%"), ("_", "_")])
def test_prefix_is_normalized_without_changing_case_or_wildcards(
        client: TestClient,
        user_repository: NonCallableMock,
        encoded: str,
        expected: str) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get(f"/v1/account/find/{encoded}")
    assert response.status_code == 200
    assert response.json() == {"accounts": []}
    user_repository.find_by_username_prefix.assert_awaited_once_with(expected, limit=20, offset=0)


def test_expired_session_does_not_search(
        client: TestClient,
        auth_use_case: NonCallableMock,
        user_repository: NonCallableMock) -> None:
    auth_use_case.authenticate.side_effect = AuthenticationException(details={"reason": "session_expired"})
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    assert client.get("/v1/account/find/ali").status_code == 401
    user_repository.find_by_username_prefix.assert_not_awaited()


def test_unconfigured_search_is_not_an_empty_result(auth_use_case: NonCallableMock) -> None:
    app = FastAPI()
    setup_exception_handlers(app)
    app.include_router(router_v1)
    app.dependency_overrides[get_auth_usecase] = lambda: auth_use_case
    with TestClient(app, base_url="https://testserver") as client:
        client.cookies.set(SESSION_COOKIE_NAME, "session-token")
        response = client.get("/v1/account/find/ali")
    assert response.status_code == 501
    assert response.json() == {
        "error": "not_implemented", "message": "Operation is not implemented",
        "details": {"entity": "user", "operation": "find_by_username_prefix"},
    }


def test_account_openapi_uses_cookie_and_string_roles(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    for path in ("/v1/account/me", "/v1/account/find/{username_prefix}"):
        assert schema["paths"][path]["get"]["security"] == [{"SessionCookie": []}]
    role = schema["components"]["schemas"]["UserRoleResponse"]
    assert role["type"] == "string"
    assert role["enum"] == ["user", "moderator", "admin"]
    assert "403" in schema["paths"]["/v1/account/find/{username_prefix}"]["get"]["responses"]
    assert "400" in schema["paths"]["/v1/account/find/{username_prefix}"]["get"]["responses"]
    assert "422" not in schema["paths"]["/v1/account/find/{username_prefix}"]["get"]["responses"]


@pytest.mark.parametrize("params, limit, offset", [
    ({"limit": "1", "offset": "10000"}, 1, 10_000),
    ({"limit": "100", "offset": "0"}, 100, 0),
    ({"offset": "12"}, 20, 12),
    ({"limit": "5"}, 5, 0),
])
def test_pagination_query_is_parsed_and_forwarded_to_repository(
        client: TestClient,
        user_repository: NonCallableMock,
        params: dict[str, str],
        limit: int,
        offset: int) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get("/v1/account/find/ali", params=params)
    assert response.status_code == 200
    assert response.json() == {"accounts": []}
    user_repository.find_by_username_prefix.assert_awaited_once_with("ali", limit=limit, offset=offset)


@pytest.mark.parametrize("params", [
    {"limit": "0"},
    {"limit": "-1"},
    {"limit": "101"},
    {"limit": "text"},
    {"limit": "1.5"},
    {"limit": "true"},
    {"offset": "-1"},
    {"offset": "10001"},
    {"offset": "text"},
    {"offset": "1.5"},
    {"unexpected": "value"},
])
def test_invalid_pagination_does_not_reach_repository(
        client: TestClient,
        user_repository: NonCallableMock,
        params: dict[str, str]) -> None:
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get("/v1/account/find/ali", params=params)
    assert response.status_code == 400
    assert response.json()["error"] == "bad_request"
    assert response.json()["details"]["errors"]
    user_repository.find_by_username_prefix.assert_not_awaited()


def test_find_returns_requested_repository_page(
        client: TestClient,
        user_repository: NonCallableMock) -> None:
    now = datetime.now(UTC)
    accounts = tuple(
        UserEntity(
            username=f"alice{number}", email=f"alice{number}@example.com",
            created_at=now, updated_at=now,
        )
        for number in range(4)
    )
    user_repository.find_by_username_prefix.side_effect = (
        lambda username_prefix, *, limit, offset: accounts[offset:offset + limit]
    )
    client.cookies.set(SESSION_COOKIE_NAME, "session-token")
    response = client.get("/v1/account/find/ali", params={"limit": 2, "offset": 1})
    assert response.status_code == 200
    assert [account["id"] for account in response.json()["accounts"]] == [
        str(account.id) for account in accounts[1:3]
    ]
    user_repository.find_by_username_prefix.assert_awaited_once_with("ali", limit=2, offset=1)


def test_pagination_is_documented_as_query_model_without_get_body(client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"]["/v1/account/find/{username_prefix}"]["get"]
    assert "requestBody" not in operation
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert parameters["username_prefix"]["in"] == "path"
    for field, default, minimum, maximum in (("limit", 20, 1, 100), ("offset", 0, 0, 10_000)):
        parameter = parameters[field]
        assert parameter["in"] == "query"
        assert not parameter["required"]
        assert parameter["schema"]["type"] == "integer"
        assert parameter["schema"]["default"] == default
        assert parameter["schema"]["minimum"] == minimum
        assert parameter["schema"]["maximum"] == maximum
