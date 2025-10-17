import os
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    # General performance and caching
    AUTO_CLEAR_GPU_MEM: bool = True # !important release gpu memory from async workers
    AUTO_GARBAGE_COLLECT: bool = True
    ENABLE_CACHE_RESULTS: bool = False
    CACHE_TTL: int = 3600  # seconds
    UPLOAD_FILE_TTL: int = 3600 # seconds, Time to live for uploaded file keys in Redis

    # Asynchronous job settings
    ASYNC_ALLOW: bool = False
    ASYNC_CLEANUP_AGE: int = 3  # in days
    ASYNC_JOB_PATH: str = "/tmp/openad_async_archive"

    # Redis and job queue settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Any | None = None
    REDIS_HIGH_PRIORITY_QUEUE: str = "high_priority_jobs"
    REDIS_LOW_PRIORITY_QUEUE: str = "low_priority_jobs"

    # Worker and job processing settings
    WORKER_COUNT: int = Field(default=1, ge=1) # Number of worker processes to spawn
    JOB_MAX_RETRIES: int = Field(default=3, ge=0) # Maximum number of retries for a failed job
    JOB_RETRY_DELAY: int = Field(default=5, ge=0) # Seconds to wait before retrying a failed job

    # Directory to store uploaded files / collections
    UPLOAD_STORAGE_DIR: str = os.path.join(os.path.expanduser("~"), ".openad_models", "collection_uploads")
    UPLOAD_STORAGE_SYNC_INTERVAL: int = Field(default=60, ge=0) # seconds

    # uvicorn settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    ENABLE_MODEL_CACHING: bool = Field(
        default=False,
        description="Enable in-memory caching of models within a worker. Set to False to reduce memory usage at the cost of reloading models for each job.",
    )
    PROBE_PORT: int = 8081
    UVICORN_LOG_LEVEL: str = "info"
    SERVE_MAX_WORKERS: int = Field(default=1, ge=1) # number fastapi of worker processes
    SERVE_WORKER_GPU_MIN: int = Field(default=2000, ge=1)  # in MB

@lru_cache(maxsize=None)
def get_config_instance() -> ServerConfig:
    return ServerConfig()
