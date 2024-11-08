from pydantic_settings import BaseSettings
from functools import lru_cache

class ServerConfig(BaseSettings):
    AUTO_CLEAR_GPU_MEM: bool = True
    AUTO_GARABAGE_COLLECT: bool = True
    SERVE_MAX_WORKERS: int = -1
    ENABLE_CACHE_RESULTS: bool = False


@lru_cache(maxsize=None)
def get_config_instance() -> ServerConfig:
    return ServerConfig()
