import base64
import binascii
from datetime import UTC, datetime
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from app.domain.entities.token import SessionTokenEntity
from app.domain.exceptions.entities import (
    AuthenticationException,
    DataFormatException,
)
from app.domain.ports.jwt import JwtProviderPort


class EdDSAJwtProviderPortAdapter(JwtProviderPort):
    def __init__(self, *, private_key: str) -> None:
        try:
            key = serialization.load_pem_private_key(
                base64.b64decode(private_key, validate=True),
                password=None,
            )
            if not isinstance(key, Ed25519PrivateKey):
                raise TypeError("Expected an Ed25519 private key")
        except (ValueError, TypeError, binascii.Error) as exc:
            raise DataFormatException(details={
                "field": "jwt_private_key",
                "reason": "invalid_ed25519_key",
            }) from exc
        self._private_key = key
        self._public_key = key.public_key()

    def encode(self, token: SessionTokenEntity) -> str:
        return jwt.encode(
            {
                "jti": str(token.session_id),
                "secret": token.secret,
                "iat": int(token.issued_at.timestamp()),
            },
            self._private_key,
            algorithm="EdDSA",
        )

    def decode(self, token: str) -> SessionTokenEntity:
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=["EdDSA"],
                options={"require": ["jti", "secret", "iat"]},
            )
            if set(payload) != {"jti", "secret", "iat"}:
                raise ValueError("Unexpected token claims")
            if not isinstance(payload["jti"], str):
                raise TypeError("Invalid session ID")
            session_id = UUID(payload["jti"])
            if session_id.version != 4:
                raise ValueError("Expected UUIDv4")
            secret = payload["secret"]
            if not isinstance(secret, str) or not secret.strip():
                raise ValueError("Invalid session secret")
            if type(payload["iat"]) is not int:
                raise ValueError("Invalid issued-at timestamp")
            return SessionTokenEntity(
                session_id=session_id,
                secret=secret,
                issued_at=datetime.fromtimestamp(
                    payload["iat"], tz=UTC,
                ),
            )
        except (
            jwt.InvalidTokenError, ValueError, TypeError,
            OverflowError, OSError,
        ) as exc:
            raise AuthenticationException(
                details={"reason": "invalid_token"},
            ) from exc
