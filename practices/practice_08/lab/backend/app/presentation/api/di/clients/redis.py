from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.domain.exceptions.entities import ServiceUnavailableException


async def get_redis_client() -> AsyncIterator[Redis]:
    from app.infrastructure.cache.factory import redis_factory

    client = redis_factory.get_client()
    try:
        yield client
    finally:
        try:
            await client.aclose()
        except RedisError as exc:
            raise ServiceUnavailableException(
                details={"storage": "redis", "operation": "close"},
            ) from exc


RedisClientDI = Annotated[
    Redis,
    Depends(get_redis_client, scope="function"),
]
