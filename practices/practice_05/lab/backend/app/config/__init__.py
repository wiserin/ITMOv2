import os
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_MODEL_CONFIG = SettingsConfigDict(
    alias_generator=lambda field_name: field_name.upper(),
    env_file='.env' if os.path.exists('.env') else None,
)


class AppConfig(BaseSettings):
    model_config = CONFIG_MODEL_CONFIG

    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    postgres_db: str

    redis_password: str
    redis_host: str
    redis_port: int
    redis_db: int

    jwt_private_key: SecretStr = SecretStr("")
    session_idle_timeout_minutes: int = Field(default=30, gt=0)
    argon2_time_cost: int = Field(default=3, gt=0)
    argon2_memory_cost: int = Field(default=65536, ge=8)
    argon2_parallelism: int = Field(default=1, gt=0)
    argon2_hash_len: int = Field(default=32, ge=4)
    argon2_salt_len: int = Field(default=16, ge=8)

    @model_validator(mode="after")
    def validate_argon2_memory(self) -> Self:
        if self.argon2_memory_cost < 8 * self.argon2_parallelism:
            raise ValueError(
                "Argon2 memory must be >= 8 * parallelism",
            )
        return self


app_config = AppConfig() #pyright: ignore[reportCallIssue]
