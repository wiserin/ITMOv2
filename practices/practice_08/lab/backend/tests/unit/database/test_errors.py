from __future__ import annotations

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.domain.exceptions.base import BaseDomainException
from app.domain.exceptions.entities import (
    AlreadyExistsException,
    ConflictException,
    DataFormatException,
    ServiceUnavailableException,
)
from app.infrastructure.database.errors import (
    translate_database_error,
)


class DriverError(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__("private driver error")
        self.sqlstate = sqlstate


@pytest.mark.parametrize("driver_type, sqlstate, expected", [
    (IntegrityError, "23505", AlreadyExistsException),
    (IntegrityError, "23503", ConflictException),
    (IntegrityError, "23502", DataFormatException),
    (IntegrityError, "23514", DataFormatException),
    (DBAPIError, "22001", DataFormatException),
    (DBAPIError, "08006", ServiceUnavailableException),
    (DBAPIError, "", ServiceUnavailableException),
])
def test_database_errors_become_generic_domain_errors(
        driver_type: type[DBAPIError],
        sqlstate: str,
        expected: type[BaseDomainException]) -> None:
    error = driver_type(
        "private SQL statement",
        {"password": "private-password"},
        DriverError(sqlstate),
    )
    domain_error = translate_database_error(error)
    assert isinstance(domain_error, expected)
    assert domain_error.details == {
        "storage": "postgresql", "sqlstate": sqlstate,
    }
    assert "private" not in domain_error.message
    assert "private" not in str(domain_error.details)


@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
def test_retryable_database_errors_use_details(
        sqlstate: str) -> None:
    error = DBAPIError(None, None, DriverError(sqlstate))
    domain_error = translate_database_error(error)
    assert isinstance(domain_error, ServiceUnavailableException)
    assert domain_error.details["retryable"] is True
    assert domain_error.details["sqlstate"] == sqlstate
