import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import URL, Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import app_config
from app.infrastructure.database.models import Base

config = context.config

postgres_url = URL.create(
    drivername="postgresql+asyncpg",
    username=app_config.postgres_user,
    password=app_config.postgres_password,
    host=app_config.postgres_host,
    port=app_config.postgres_port,
    database=app_config.postgres_db,
)


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    context.configure(
        url=postgres_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(
        postgres_url, poolclass=pool.NullPool,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=Base.metadata,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
