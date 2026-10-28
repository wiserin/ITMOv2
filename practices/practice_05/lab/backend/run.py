from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.infrastructure.cache.factory import redis_factory
from app.infrastructure.database.factory import database_factory
from app.presentation.api.routes import router_v1
from app.presentation.setup_exceptions import setup_exception_handlers

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        await database_factory.check_connection()
        await redis_factory.check_connection()
        logger.info("AnimeMap API started")
        yield
    finally:
        try:
            await redis_factory.close()
        finally:
            await database_factory.dispose()


service = FastAPI(lifespan=lifespan, title="AnimeMap API")
setup_exception_handlers(service)
service.include_router(router_v1)


@service.get("/ping", tags=["system"])
async def ping() -> JSONResponse:
    return JSONResponse(status_code=200, content="pong")
