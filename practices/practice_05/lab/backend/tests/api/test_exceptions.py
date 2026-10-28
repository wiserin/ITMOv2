from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.exceptions.base import BaseDomainException
from app.domain.exceptions.entities import (
    AlreadyExistsException,
    AuthenticationException,
    ConflictException,
    DataFormatException,
    NotFoundException,
    NotImplementedException,
    PermissionException,
    ServiceUnavailableException,
)
from app.presentation.setup_exceptions import setup_exception_handlers


@pytest.mark.parametrize("exception_type, status_code, code", [
    (AlreadyExistsException, 409, "conflict"),
    (ConflictException, 409, "conflict"),
    (DataFormatException, 400, "bad_request"),
    (NotFoundException, 404, "not_found"),
    (AuthenticationException, 401, "authentication_failed"),
    (PermissionException, 403, "access_denied"),
    (NotImplementedException, 501, "not_implemented"),
    (ServiceUnavailableException, 503, "service_unavailable"),
    (BaseDomainException, 500, "internal_error"),
])
def test_domain_errors_are_mapped_in_one_place(
        exception_type: type[BaseDomainException],
        status_code: int,
        code: str) -> None:
    app = FastAPI()
    setup_exception_handlers(app)
    error = exception_type("Readable message", details={"entity": "user", "id": "example"})

    @app.get("/failure")
    async def fail() -> None:
        raise error

    with TestClient(app) as client:
        response = client.get("/failure")
    assert response.status_code == status_code
    assert response.json() == {
        "error": code, "message": error.message, "details": error.details,
    }


@pytest.mark.parametrize("entity", ["user", "location"])
def test_one_error_type_carries_different_entity_context(entity: str) -> None:
    app = FastAPI()
    setup_exception_handlers(app)

    @app.get("/failure")
    async def fail() -> None:
        raise NotFoundException(details={"entity": entity, "operation": "get"})

    with TestClient(app) as client:
        response = client.get("/failure")
    assert response.status_code == 404
    assert response.json()["message"] == "Entity not found"
    assert response.json()["details"] == {"entity": entity, "operation": "get"}


def test_validation_is_400_without_echoing_request_secrets(client: TestClient) -> None:
    response = client.post("/v1/auth/login", json={
        "email": "invalid", "password": "private-password", "token": "private-token",
    })
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "bad_request"
    assert data["message"] == "Ошибка валидации данных."
    assert {tuple(error["loc"]) for error in data["details"]["errors"]} == {
        ("body", "email"), ("body", "token"),
    }
    assert "private-password" not in response.text
    assert "private-token" not in response.text
