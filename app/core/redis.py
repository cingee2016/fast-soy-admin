from typing import Annotated

from fastapi import Depends, Request
from redis import asyncio as aioredis
from redis.asyncio import Redis

from app.settings import APP_SETTINGS


async def init_redis() -> Redis:
    return aioredis.from_url(url=APP_SETTINGS.REDIS_URL)


async def close_redis(redis: Redis) -> None:
    await redis.close()


def get_redis(request: Request) -> Redis:
    return request.app.state.redis  # type: ignore[no-any-return]


AioRedis = Annotated[Redis, Depends(get_redis)]
