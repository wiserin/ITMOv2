from sqlalchemy.exc import DBAPIError, IntegrityError

from app.domain.exceptions.base import BaseDomainException
from app.domain.exceptions.entities import (
    AlreadyExistsException,
    ConflictException,
    DataFormatException,
    ServiceUnavailableException,
)


def extract_sqlstate(exc: DBAPIError) -> str:
    orig = exc.orig
    for source in (orig, getattr(orig, "driver_exception", None), getattr(orig, "__cause__", None)):
        sqlstate = getattr(source, "sqlstate", None)
        if sqlstate:
            return str(sqlstate)
    return ""


def translate_database_error(exc: DBAPIError) -> BaseDomainException:
    sqlstate = extract_sqlstate(exc)
    details: dict[str, object] = {"storage": "postgresql", "sqlstate": sqlstate}
    if sqlstate == "23505":
        return AlreadyExistsException(details=details)
    if sqlstate in {"23502", "23514", "22001"}:
        return DataFormatException(details=details)
    if sqlstate == "23503" or isinstance(exc, IntegrityError):
        return ConflictException(details=details)
    if sqlstate in {"40001", "40P01"}:
        details["retryable"] = True
    return ServiceUnavailableException(details=details)
