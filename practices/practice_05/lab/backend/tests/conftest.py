import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from app.infrastructure.security.jwt import (
    EdDSAJwtProviderPortAdapter,
)
from app.infrastructure.security.secret import (
    Argon2SecretManagerPortAdapter,
)


@pytest.fixture
def jwt_provider() -> EdDSAJwtProviderPortAdapter:
    pem = Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return EdDSAJwtProviderPortAdapter(
        private_key=base64.b64encode(pem).decode(),
    )


@pytest.fixture
def secret_manager() -> Argon2SecretManagerPortAdapter:
    return Argon2SecretManagerPortAdapter(
        time_cost=1, memory_cost=1024,
    )
