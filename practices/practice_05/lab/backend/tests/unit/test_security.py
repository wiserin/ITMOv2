import asyncio
import base64
from datetime import UTC, datetime
from uuid import uuid4

import jwt
import pytest

from app.domain.entities.token import SessionTokenEntity
from app.domain.exceptions.entities import (
    AuthenticationException,
    DataFormatException,
)
from app.domain.ports.jwt import JwtProviderPort
from app.domain.ports.secret import SecretManagerPort
from app.infrastructure.security.jwt import (
    EdDSAJwtProviderPortAdapter,
)


def test_jwt_roundtrip(jwt_provider: JwtProviderPort) -> None:
    token = SessionTokenEntity(
        session_id=uuid4(), secret="random secret",
        issued_at=datetime.now(UTC).replace(microsecond=0),
    )
    encoded = jwt_provider.encode(token)
    assert jwt_provider.decode(encoded) == token
    payload = jwt.decode(encoded, options={"verify_signature": False})
    assert set(payload) == {"jti", "secret", "iat"}
    assert jwt.get_unverified_header(encoded)["alg"] == "EdDSA"
    assert "random secret" not in repr(token)


@pytest.mark.parametrize("change", [
    {"jti": "invalid"}, {"jti": str(uuid4()).replace("-", "x")},
    {"secret": 123}, {"secret": " "}, {"iat": True},
    {"iat": "123"}, {"iat": 1.5}, {"iat": 10 ** 30},
    {"exp": 10 ** 12}, {"sub": "user"}, {"secret": None},
])
def test_jwt_rejects_signed_invalid_claims(
        jwt_provider: JwtProviderPort,
        change: dict[str, object]) -> None:
    payload = {"jti": str(uuid4()), "secret": "secret", "iat": 1}
    payload.update(change)
    encoded = jwt.encode(
        payload, jwt_provider._private_key, algorithm="EdDSA",
    )
    with pytest.raises(AuthenticationException):
        jwt_provider.decode(encoded)


def test_jwt_rejects_missing_claims_and_wrong_algorithm(
        jwt_provider: JwtProviderPort) -> None:
    tokens = [
        "broken",
        jwt.encode({}, jwt_provider._private_key, algorithm="EdDSA"),
        jwt.encode(
            {"jti": str(uuid4()), "secret": "secret", "iat": 1},
            "x" * 32, algorithm="HS256",
        ),
    ]
    for token in tokens:
        with pytest.raises(AuthenticationException):
            jwt_provider.decode(token)


def test_jwt_rejects_different_signer(
        jwt_provider: JwtProviderPort) -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )

    encoded = jwt.encode(
        {"jti": str(uuid4()), "secret": "secret", "iat": 1},
        Ed25519PrivateKey.generate(), algorithm="EdDSA",
    )
    with pytest.raises(AuthenticationException):
        jwt_provider.decode(encoded)


@pytest.mark.parametrize("key", [
    "", "not base64", base64.b64encode(b"not pem").decode(),
])
def test_invalid_private_key(key: str) -> None:
    with pytest.raises(DataFormatException):
        EdDSAJwtProviderPortAdapter(private_key=key)


def test_argon2_hash_and_verify(
        secret_manager: SecretManagerPort) -> None:
    async def scenario() -> None:
        first = await secret_manager.hash_secret(" secret ")
        second = await secret_manager.hash_secret(" secret ")
        assert first != second
        assert first.startswith("$argon2id$")
        await secret_manager.verify_secret(" secret ", first)
        with pytest.raises(AuthenticationException):
            await secret_manager.verify_secret("secret", first)
        with pytest.raises(DataFormatException):
            await secret_manager.verify_secret("secret", "broken")

    asyncio.run(scenario())


def test_random_secrets(secret_manager: SecretManagerPort) -> None:
    first = secret_manager.generate_random_secret()
    assert first != secret_manager.generate_random_secret()
    assert len(base64.urlsafe_b64decode(first + "=")) >= 32
    with pytest.raises(DataFormatException):
        secret_manager.generate_random_secret(31)
