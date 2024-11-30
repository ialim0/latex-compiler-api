# app/services/cache.py
import redis.asyncio as redis # type: ignore

from app.config import settings

class RedisCache:
    def __init__(self):
        self.redis_pool = None

    async def init_pool(self):
        if self.redis_pool is None:
            self.redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_SIZE
            )

    async def get_connection(self) -> redis.Redis:
        if self.redis_pool is None:
            await self.init_pool()
        return redis.Redis(connection_pool=self.redis_pool)

    async def get(self, key: str) -> str:
        async with await self.get_connection() as conn:
            return await conn.get(key)

    async def set(self, key: str, value: str, expire: int = 3600):
        async with await self.get_connection() as conn:
            await conn.set(key, value, ex=expire)