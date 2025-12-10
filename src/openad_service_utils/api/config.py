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

    # Asynchronous job settings
    ASYNC_ALLOW: bool = False
    ASYNC_CLEANUP_AGE: int = 3  # in days
    ASYNC_JOB_PATH: str = "/tmp/openad_async_jobs"

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
    JOB_TTL: int = Field(default=86400, ge=0) # Time to live for job keys in Redis (seconds)
    REQUEST_CACHE_TTL: int = 3600  # Time to live for job request in Redis (seconds)
    JOB_COMPLETION_TIMEOUT: int = Field(default=3600, ge=0) # Timeout for waiting for a syncrounous job to complete (seconds)

    # Directory to store uploaded files / collections
    COLLECTIONS_API_ENABLED: bool = False
    UPLOAD_STORAGE_DIR: str = os.path.join(os.path.expanduser("~"), ".openad_models", "collection_uploads")
    UPLOAD_STORAGE_CHUNK_TEMP_DIR: str = "/tmp/openad_upload_chunks"
    UPLOAD_STORAGE_EXPIRATION: int = Field(default=(24 * 60 * 60), ge=0)     # seconds (24 hrs) - Expiration time for incomplete uploads
    UPLOAD_STORAGE_EXPIRATION_COMPLETE: int = Field(default=(60 * 10), ge=0) # seconds (10 min) - Expiration time for completed uploads
    UPLOAD_STORAGE_INTERVAL_SYNC: int = Field(default=60, ge=0)              # seconds  (1 min) - How often to run bg task: Sync upload progress to Redis
    UPLOAD_STORAGE_INTERVAL_CLEANUP: int = Field(default=(60 * 10), ge=0)    # seconds (10 min) - How often to run bg task: Cleanup of expired uploads

    # For testing
    UPLOAD_STORAGE_EXPIRATION: int = Field(default=(60), ge=0)               # seconds (1 min) - Expiration time for incomplete uploads
    UPLOAD_STORAGE_EXPIRATION_COMPLETE: int = Field(default=(60), ge=0)      # seconds (1 min) - Expiration time for completed uploads
    UPLOAD_STORAGE_INTERVAL_CLEANUP: int = Field(default=(60), ge=0)         # seconds (1 min) - How often to run bg task: Cleanup of expired uploads

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
    ADMIN_ENDPOINTS_ENABLED: bool = False # Default to disabled for production

@lru_cache(maxsize=None)
def get_config_instance() -> ServerConfig:
    return ServerConfig()
