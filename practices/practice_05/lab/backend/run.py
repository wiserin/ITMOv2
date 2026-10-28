from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.logging.logging_setup import setup_logging
from app.presentation.setup_exceptions import setup_exception_handlers
from app.presentation.api.routes import router_v1
from app.infrastructure.cache.factory import redis_factory
from app.infrastructure.database.factory import database_factory
from app.config.bootstrap.service_init import init_service

import app.infrastructure.database.models  # noqa: F401
import logging


setup_logging()


logger = logging.getLogger()

async def init():
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_factory.check_connection()
    await init_service()
    logger.info("Service init complite")
    yield
    await redis_factory.close()
    await database_factory.dispose()


service = FastAPI(
    lifespan=lifespan,
    title="Evroprom ID"
)
setup_exception_handlers(service)
service.include_router(router_v1)


@service.get("/ping")
async def send():
    return JSONResponse(
        status_code=200,
        content="pong"
    )
