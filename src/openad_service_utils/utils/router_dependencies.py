# 3rd Party
from fastapi import Request, Depends, HTTPException
import redis.asyncio as redis

# Local
from openad_service_utils.api.job_manager import JobManager
from openad_service_utils.common.properties.property_factory import PropertyFactory


async def get_redis_client(request: Request) -> redis.Redis:
    """Dependency to get Redis client from app state."""
    return request.app.state.redis


async def get_job_manager(
    redis_client: redis.Redis = Depends(get_redis_client),
) -> JobManager:
    """Dependency to get JobManager instance."""
    return JobManager(redis_client, "Master Queue")


def files_enabled():
    """Dependency to check if file collection endpoints are enabled."""
    if "get_mesh_property" not in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
        raise HTTPException(
            status_code=404,
            detail="File collection endpoints are not available for this service configuration.",
        )
