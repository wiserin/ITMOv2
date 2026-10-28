from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy import Connection
from alembic import context
import asyncio

from app.infrastructure.database.models import Base
from app.config import app_config

import app.infrastructure.database.models #noqa: F401

config = context.config

db_username = app_config.postgres_user
db_user_password = app_config.postgres_password
db_host = app_config.postgres_host
db_port = app_config.postgres_port
db_name = app_config.postgres_db


postgres_conn: str = f'postgresql+asyncpg://{db_username}:{db_user_password}@{db_host}:{db_port}/{db_name}'
config.set_main_option("sqlalchemy.url", postgres_conn)
engine: AsyncEngine = create_async_engine(postgres_conn)


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline():
    context.configure(url=postgres_conn, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
