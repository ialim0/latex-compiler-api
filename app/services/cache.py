# app/services/cache.py

import redis.asyncio as redis
from app.config import settings

class RedisCache:
    _redis_client = None

    async def init_client(self):
        if self._redis_client is None:
            self._redis_client = await redis.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_POOL_SIZE,
                decode_responses=True  
            )

    async def get_client(self) -> redis.Redis:
        if self._redis_client is None:
            await self.init_client()
        return self._redis_client

    async def get(self, key: str) -> str:
        client = await self.get_client()
        return await client.get(key)

    async def set(self, key: str, value: str, expire: int = 3600):
        client = await self.get_client()
        await client.set(key, value, ex=expire)
