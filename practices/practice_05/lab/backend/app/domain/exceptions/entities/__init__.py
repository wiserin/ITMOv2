from app.domain.exceptions.base import BaseDomainException


class AlreadyExistsException(BaseDomainException):
    default_message = "Entity already exists"


class ConflictException(BaseDomainException):
    default_message = "Operation conflicts with the current state"


class DataFormatException(BaseDomainException):
    default_message = "Invalid data format"


class NotFoundException(BaseDomainException):
    default_message = "Entity not found"


class AuthenticationException(BaseDomainException):
    default_message = "Authentication failed"


class PermissionException(BaseDomainException):
    default_message = "Access denied"


class NotImplementedException(BaseDomainException):
    default_message = "Operation is not implemented"


class ServiceUnavailableException(BaseDomainException):
    default_message = "Service is temporarily unavailable"
