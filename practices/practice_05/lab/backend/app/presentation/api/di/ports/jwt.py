from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.domain.ports.jwt import JwtProviderPort
from app.infrastructure.security.jwt import (
    EdDSAJwtProviderPortAdapter,
)


@lru_cache
def get_jwt_provider() -> JwtProviderPort:
    from app.config import app_config

    return EdDSAJwtProviderPortAdapter(
        private_key=app_config.jwt_private_key.get_secret_value(),
    )


JwtProviderDI = Annotated[JwtProviderPort, Depends(get_jwt_provider)]
