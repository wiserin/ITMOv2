import asyncio
import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from app.domain.exceptions.entities import (
    AuthenticationException,
    DataFormatException,
    ServiceUnavailableException,
)
from app.domain.ports.secret import SecretManagerPort


class Argon2SecretManagerPortAdapter(SecretManagerPort):
    def __init__(
            self,
            *,
            time_cost: int = 3,
            memory_cost: int = 65536,
            parallelism: int = 1,
            hash_len: int = 32,
            salt_len: int = 16) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
            type=Type.ID,
        )

    async def hash_secret(self, raw_secret: str) -> str:
        try:
            return await asyncio.to_thread(
                self._hasher.hash, raw_secret,
            )
        except HashingError as exc:
            raise ServiceUnavailableException(
                details={"operation": "hash_secret"},
            ) from exc

    async def verify_secret(
            self,
            raw_secret: str,
            hashed_secret: str) -> None:
        try:
            await asyncio.to_thread(
                self._hasher.verify, hashed_secret, raw_secret,
            )
        except VerifyMismatchError as exc:
            raise AuthenticationException(
                details={"reason": "invalid_secret"},
            ) from exc
        except (InvalidHashError, VerificationError) as exc:
            raise DataFormatException(
                details={"field": "secret_hash"},
            ) from exc

    def generate_random_secret(self, nbytes: int = 32) -> str:
        if type(nbytes) is not int or nbytes < 32:
            raise DataFormatException(details={
                "field": "nbytes", "minimum": 32,
            })
        return secrets.token_urlsafe(nbytes)
