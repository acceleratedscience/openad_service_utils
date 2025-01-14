from pydantic_settings import BaseSettings
from functools import lru_cache


class ServerConfig(BaseSettings):
    AUTO_CLEAR_GPU_MEM: bool = False
    AUTO_GARABAGE_COLLECT: bool = False
    SERVE_MAX_WORKERS: int = -1
    ENABLE_CACHE_RESULTS: bool = False
    ASYNC_POOL_MAX: int = 1
    MAX_CACHE_MEMORY_GB: str = "AUTO"  # Maximum memory in GB for model caching, "AUTO" for automatic sizing


@lru_cache(maxsize=None)
def get_config_instance() -> ServerConfig:
    return ServerConfig()
