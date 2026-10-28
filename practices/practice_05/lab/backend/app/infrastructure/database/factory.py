from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from sqlalchemy import URL
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker,
    create_async_engine)
from logging import getLogger, Logger


from app.config import app_config


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
                sqlstate = self._extract_sqlstate(exc)
                logger.warning("IntegrityError (sqlstate=%s), transaction rolled back", sqlstate)
                raise DatabaseException(sql_code=sqlstate or "") from exc

            except DBAPIError as exc:
                await session.rollback()
                sqlstate = self._extract_sqlstate(exc)
                logger.error("DBAPIError (sqlstate=%s), transaction rolled back", sqlstate)

                if sqlstate in ("40001", "40P01"):
                    raise RetryableException(sql_code=sqlstate) from exc
                raise DatabaseException(sql_code=sqlstate or "") from exc

            except Exception as exc:
                await session.rollback()
                logger.exception("Unexpected exception in database session, transaction rolled back: %s", exc)
                raise

    async def dispose(self) -> None:
        await self._engine.dispose()

    @staticmethod
    def _extract_sqlstate(exc: DBAPIError) -> str:
        orig = getattr(exc, "orig", None)
        if not orig:
            return ""

        for obj in (orig, getattr(orig, "driver_exception", None), getattr(orig, "__cause__", None)):
            sqlstate = getattr(obj, "sqlstate", None)
            if sqlstate:
                return str(sqlstate)

        return ""


database_factory = SessionController(
    postgres_user=app_config.postgres_user,
    postgres_password=app_config.postgres_password,
    postgres_host=app_config.postgres_host,
    postgres_port=app_config.postgres_port,
    postgres_db=app_config.postgres_db
)
