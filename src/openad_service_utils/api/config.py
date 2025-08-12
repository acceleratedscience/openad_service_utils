from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Any


class ServerConfig(BaseSettings):
    AUTO_CLEAR_GPU_MEM: bool = True
    AUTO_GARBAGE_COLLECT: bool = True
    SERVE_MAX_WORKERS: int = -1
    ENABLE_CACHE_RESULTS: bool = False
    CACHE_TTL: int = 3600  # seconds
    ASYNC_POOL_MAX: int = 1

    ASYNC_ALLOW: bool = False
    ASYNC_CLEANUP_AGE: int = 3  # in days
    ASYNC_QUEUE_ALLOCATION: int = 1
    ASYNC_JOB_PATH: str = "/tmp/openad_async_archive"

    REDIS_JOB_QUEUES: int = 1
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Any | None = None


@lru_cache(maxsize=None)
def get_config_instance() -> ServerConfig:
    return ServerConfig()
