import os

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


app_config = AppConfig() #pyright: ignore[reportCallIssue]
