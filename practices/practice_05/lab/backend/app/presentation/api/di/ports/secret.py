from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.domain.ports.secret import SecretManagerPort
from app.infrastructure.security.secret import (
    Argon2SecretManagerPortAdapter,
)


@lru_cache
def get_secret_manager() -> SecretManagerPort:
    from app.config import app_config

    return Argon2SecretManagerPortAdapter(
        time_cost=app_config.argon2_time_cost,
        memory_cost=app_config.argon2_memory_cost,
        parallelism=app_config.argon2_parallelism,
        hash_len=app_config.argon2_hash_len,
        salt_len=app_config.argon2_salt_len,
    )


SecretManagerDI = Annotated[
    SecretManagerPort, Depends(get_secret_manager),
]
