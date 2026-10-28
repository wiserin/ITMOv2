from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import Logger, getLogger

from sqlalchemy import URL, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.domain.exceptions.base import BaseDomainException
from app.infrastructure.database.errors import (
    extract_sqlstate,
    translate_database_error,
)

logger: Logger = getLogger("DATABASE-SESSION-MANAGER")


class SessionController:
    def __init__(
            self,
            postgres_user: str,
            postgres_password: str,
            postgres_host: str,
            postgres_port: int,
            postgres_db: str,
            echo: bool = False,
            pool_size: int = 15,
            max_overflow: int = 10,
            pool_recycle: int = 1800) -> None:

        db_url = URL.create(
            drivername="postgresql+asyncpg",
            username=postgres_user,
            password=postgres_password,
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
        )

        self._engine = create_async_engine(
            url=db_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=pool_recycle,
            connect_args={"server_settings": {"jit": "off"}},
        )

        self._factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        async with self._factory() as session:
            try:
                logger.debug("New session started")
                yield session
                await session.commit()
                logger.debug("Session committed successfully")
            except IntegrityError as exc:
                await session.rollback()
                sqlstate = extract_sqlstate(exc)
                logger.warning(
                    "IntegrityError (sqlstate=%s), rolled back",
                    sqlstate,
                )
                raise translate_database_error(exc) from exc

            except DBAPIError as exc:
                await session.rollback()
                sqlstate = extract_sqlstate(exc)
                logger.error(
                    "DBAPIError (sqlstate=%s), rolled back", sqlstate,
                )

                raise translate_database_error(exc) from exc

            except BaseDomainException:
                await session.rollback()
                raise

            except Exception:
                await session.rollback()
                logger.exception(
                    "Unexpected database session error, rolled back",
                )
                raise

    async def dispose(self) -> None:
        await self._engine.dispose()

    async def check_connection(self) -> None:
        try:
            async with self._engine.connect() as connection:
                await connection.scalar(select(1))
        except DBAPIError as exc:
            raise translate_database_error(exc) from exc
