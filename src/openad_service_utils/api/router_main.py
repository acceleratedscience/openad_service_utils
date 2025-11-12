# Std
import logging

# 3rd Party
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

# Utils
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.utils.router_dependencies import get_redis_client

#
#

# Get configuration and logger
settings = get_config_instance()
logger = logging.getLogger(__name__)

# Router
main_router = APIRouter(
    prefix="/service/pde",
    tags=["Main"],
)


@main_router.get("/", response_class=HTMLResponse)
@main_router.get("/health", response_class=HTMLResponse)
async def health():
    "Health check"
    return "UP"


# # !!! DEVELOPMENT ONLY - DISABLE FOR PRODUCTION !!!
# @main_router.delete("/redis/clear")
# async def clear_redis_database(redis_client: redis.Redis = Depends(get_redis_client)):
#     """
#     Clears the entire Redis database.
#     WARNING: This will delete ALL data in Redis including caches, file mappings, and job data.
#     """
#     try:
#         # Clear all keys in the current database
#         await redis_client.flushdb()

#         logger.warning("Redis database cleared by admin request")

#         return JSONResponse(
#             {
#                 "message": "Redis database cleared successfully",
#                 "warning": "All cached data, file mappings, and job information have been deleted",
#             }
#         )

#     except Exception as e:
#         logger.error("Error clearing Redis database: %s", str(e))
#         raise HTTPException(
#             status_code=500, detail=f"Error clearing Redis database: {str(e)}"
#         ) from e
