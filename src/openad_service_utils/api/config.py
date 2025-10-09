from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Any
import tempfile
import os

class ServerConfig(BaseSettings):
    AUTO_CLEAR_GPU_MEM: bool = False
    AUTO_GARBAGE_COLLECT: bool = False
    ENABLE_CACHE_RESULTS: bool = False
    CACHE_TTL: int = 3600  # seconds
    UPLOAD_FILE_TTL: int = 3600 # seconds, Time to live for uploaded file keys in Redis
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

    # Directory to store uploaded files / collections
    UPLOAD_STORAGE_DIR: str = os.path.join(tempfile.gettempdir(), "openad_uploads")
    UPLOAD_STORAGE_SYNC_INTERVAL: int = 60 # seconds

    # uvicorn settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    PROBE_PORT: int = 8081
    UVICORN_LOG_LEVEL: str = "info"
    SERVE_MAX_WORKERS: int = Field(default=1, ge=1) # number fastapi of worker processes
    SERVE_WORKER_GPU_MIN: int = Field(default=2000, ge=0)  # in MB

@lru_cache(maxsize=None)
def get_config_instance() -> ServerConfig:
    return ServerConfig()
