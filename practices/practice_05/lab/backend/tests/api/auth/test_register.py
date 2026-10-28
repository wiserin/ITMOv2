from __future__ import annotations

from unittest.mock import NonCallableMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.application.dto.register import RegisterDTO


def test_registration_redirects_only_after_success(
        client: TestClient,
        register_use_case: NonCallableMock,
        login_use_case: NonCallableMock) -> None:
    response = client.post("/v1/auth/register", json={
        "email": " NEW@EXAMPLE.COM ", "username": " anime-fan ",
        "password": " original password ", "display_name": " Anime Fan ",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "https://testserver/v1/auth/login"
    assert response.content == b""
    assert "set-cookie" not in response.headers
    register_use_case.register.assert_awaited_once()
    data = register_use_case.register.call_args.args[0]
    assert isinstance(data, RegisterDTO)
    assert data.email == "new@example.com"
    assert data.username == "anime-fan"
    assert data.display_name == "Anime Fan"
    assert data.password == " original password "
    assert " original password " not in repr(data)
    login_use_case.login.assert_not_awaited()


def test_display_name_is_optional(client: TestClient, register_use_case: NonCallableMock) -> None:
    response = client.post("/v1/auth/register", json={
        "email": "new@example.com", "username": "anime-fan", "password": "root",
    })
    assert response.status_code == 303
    assert register_use_case.register.call_args.args[0].display_name is None


@pytest.mark.parametrize("changes", [
    {"username": None},
    {"username": "   "},
    {"username": "u" * 101},
    {"display_name": "   "},
    {"display_name": "d" * 101},
    {"email": "invalid"},
    {"password": ""},
    {"password": 1234},
    {"role": "admin"},
    {"is_active": True},
    {"password_hash": "client-provided-hash"},
])
def test_registration_fields_match_user_contract(
        client: TestClient,
        register_use_case: NonCallableMock,
        changes: dict[str, object]) -> None:
    payload = {"email": "new@example.com", "username": "new", "password": "password"}
    payload.update(changes)
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 422
    register_use_case.register.assert_not_awaited()
    assert "location" not in response.headers


def test_existing_email_does_not_redirect(
        client: TestClient,
        register_use_case: NonCallableMock,
        login_use_case: NonCallableMock) -> None:
    register_use_case.register.side_effect = HTTPException(status_code=409, detail="Email already exists")
    response = client.post("/v1/auth/register", json={
        "email": "existing@example.com", "username": "new", "password": "password",
    })
    assert response.status_code == 409
    assert "location" not in response.headers
    login_use_case.login.assert_not_awaited()


def test_auth_openapi_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    login = schema["paths"]["/v1/auth/login"]["post"]
    register = schema["paths"]["/v1/auth/register"]["post"]
    assert login["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/LoginRequest",
    )
    assert login["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/LoginResponse",
    )
    assert "Location" in register["responses"]["303"]["headers"]
    assert "content" not in register["responses"]["303"]
    assert "200" not in register["responses"]
    assert schema["components"]["schemas"]["RegisterRequest"]["additionalProperties"] is False
    assert schema["components"]["schemas"]["LoginResponse"]["properties"] == {}
