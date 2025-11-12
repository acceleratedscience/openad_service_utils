# 3rd Party
from fastapi import Request, Depends
import redis.asyncio as redis

# Workers
from openad_service_utils.api.job_manager import JobManager


async def get_redis_client(request: Request) -> redis.Redis:
    """Dependency to get Redis client from app state."""
    return request.app.state.redis


async def get_job_manager(
    redis_client: redis.Redis = Depends(get_redis_client),
) -> JobManager:
    """Dependency to get JobManager instance."""
    return JobManager(redis_client, "Master Queue")
