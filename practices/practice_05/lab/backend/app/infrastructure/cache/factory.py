from redis.asyncio import ConnectionPool, Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from app.config import app_config
from app.domain.exceptions.entities import ServiceUnavailableException


class RedisFactory:
    def __init__(
            self,
            redis_host: str,
            redis_port: int,
            redis_db: int,
            redis_password: str | None = None,
            max_connections: int = 20,
            socket_timeout: float = 2.0,
            socket_connect_timeout: float = 2.0) -> None:

        retry_policy = Retry(
            backoff=ExponentialBackoff(cap=0.5, base=0.1),
            retries=3,
        )

        self._pool = ConnectionPool(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            max_connections=max_connections,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout,
            retry=retry_policy,
            retry_on_error=[ConnectionError, TimeoutError],
            health_check_interval=30,
        )


    def get_client(self) -> Redis:
        return Redis(connection_pool=self._pool)


    async def check_connection(self) -> None:
        client = self.get_client()
        try:
            try:
                await client.ping()
            finally:
                await client.aclose()
        except RedisError as exc:
            raise ServiceUnavailableException(details={"storage": "redis", "operation": "ping"}) from exc


    async def close(self) -> None:
        try:
            await self._pool.disconnect()
        except RedisError as exc:
            raise ServiceUnavailableException(details={"storage": "redis", "operation": "close"}) from exc


    async def __aenter__(self) -> Redis:
        await self.check_connection()
        return self.get_client()


    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


redis_factory = RedisFactory(
    redis_host=app_config.redis_host,
    redis_port=app_config.redis_port,
    redis_db=app_config.redis_db,
    redis_password=app_config.redis_password,
)
