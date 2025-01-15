import os
import sys
import threading
import psutil
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple
from cachetools import TTLCache, LRUCache
from functools import lru_cache, wraps
from openad_service_utils.api.config import get_config_instance
import logging

# Create a logger
logger = logging.getLogger(__name__)


class ModelCache:
    """Thread-safe singleton cache for ML models with memory management."""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, maxsize: int = 100, ttl: int = 3600):
        """Initialize the cache with size and time limits (only runs once).
        
        Args:
            maxsize: Maximum number of models to cache
            ttl: Time to live for cached models in seconds
        """
        # Skip initialization if already done
        if self._initialized:
            return
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._memory_cache = LRUCache(maxsize=maxsize)
        self._operation_lock = threading.Lock()  # Separate lock for operations
        # Handle automatic memory sizing
        config_memory = get_config_instance().MAX_CACHE_MEMORY_GB
        self._max_memory_gb = self._get_max_memory_gb(config_memory)
        logger.debug(f"Cache memory limit set to {self._max_memory_gb}GB")
        self._initialized = True
        logger.debug("Initialized shared ModelCache instance")

    def _is_running_in_kubernetes(self) -> bool:
        """Check if we're running in a Kubernetes pod."""
        try:
            # Check for container environment
            cgroup_path = Path("/proc/1/cgroup")
            if not cgroup_path.exists():
                return False
            
            # Check cgroup content for kubernetes indicators
            cgroup_content = cgroup_path.read_text()
            return any(indicator in cgroup_content.lower() 
                     for indicator in ['kubepods', 'kubernetes'])
        except Exception as e:
            logger.debug(f"Failed to check for Kubernetes environment: {str(e)}")
            return False

    def _get_kubernetes_memory_limit(self) -> Optional[int]:
        """Get memory limit in bytes from Kubernetes cgroup."""
        try:
            # Try modern cgroup v2 path first
            memory_limit_paths = [
                "/sys/fs/cgroup/memory.max",  # cgroup v2
                "/sys/fs/cgroup/memory/memory.limit_in_bytes",  # cgroup v1
            ]
            
            for path in memory_limit_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        limit = f.read().strip()
                        # Handle "max" value in cgroup v2
                        if limit == "max":
                            return None
                        return int(limit)
            
            return None
        except Exception as e:
            logger.debug(f"Failed to read Kubernetes memory limit: {str(e)}")
            return None

    def _get_system_memory(self) -> Tuple[int, int]:
        """Get available and total memory in bytes."""
        if self._is_running_in_kubernetes():
            k8s_limit = self._get_kubernetes_memory_limit()
            if k8s_limit:
                # Use 90% of container limit as available memory
                logger.debug(f"Running in Kubernetes with {k8s_limit / (1024**3):.1f}GB limit")
                return (k8s_limit, k8s_limit)
        
        # Fall back to system memory if not in K8s or failed to get limit
        vm = psutil.virtual_memory()
        return (vm.available, vm.total)

    def _get_max_memory_gb(self, config_memory: Union[str, int]) -> int:
        """Calculate maximum memory limit in GB.
        
        If config is "AUTO", uses 75% of available memory or container limit.
        Otherwise uses the configured value.
        """
        if isinstance(config_memory, str) and config_memory.upper() == "AUTO":
            # Get memory limits considering K8s environment
            available_memory, total_memory = self._get_system_memory()
            
            # Use 75% of available memory or 25% of total memory, whichever is smaller
            auto_memory = min(
                available_memory * 0.9,  # 75% of available
                total_memory * 0.9      # 25% of total
            )
            
            # Convert to GB and ensure minimum of 1GB
            memory_gb = max(1, int(auto_memory / (1024 ** 3)))
            logger.debug(
                f"Auto-configured cache memory: {memory_gb}GB "
                f"(from {available_memory / (1024**3):.1f}GB available, "
                f"{total_memory / (1024**3):.1f}GB total)"
            )
            return memory_gb
        else:
            try:
                return int(config_memory)
            except (ValueError, TypeError):
                logger.warning(f"Invalid memory configuration: {config_memory}, using default of 16GB")
                return 16

    def get(self, key: str) -> Optional[Any]:
        """Get a model from cache if it exists."""
        with self._operation_lock:
            return self._cache.get(key)
            
    def set(self, key: str, value: Any) -> None:
        """Add a model to cache with memory monitoring."""
        try:
            # Rough memory size estimation
            memory_size = sys.getsizeof(value) / (1024 ** 3)  # Convert to GB
            
            with self._operation_lock:
                # Check if adding this model would exceed memory limit
                current_memory = sum(self._memory_cache.values())
                if current_memory + memory_size > self._max_memory_gb:
                    # Remove oldest items until we have space
                    while current_memory + memory_size > self._max_memory_gb and self._memory_cache:
                        _, size = self._memory_cache.popitem()
                        current_memory -= size
                
                self._cache[key] = value
                self._memory_cache[key] = memory_size
                logger.debug(f"Model cached successfully. Current cache size: {len(self._cache)}")
                
        except Exception as e:
            logger.error(f"Failed to cache model: {str(e)}")
            # Continue without caching if there's an error


def get_model_cache() -> ModelCache:
    """Get the shared ModelCache instance."""
    return ModelCache()

def conditional_lru_cache(maxsize=100):
    def decorator(func):
        if get_config_instance().ENABLE_CACHE_RESULTS:
            cached_func = lru_cache(maxsize=maxsize)(func)
            return cached_func
        else:

            @wraps(func)
            def no_cache(*args, **kwargs):
                return func(*args, **kwargs)

            return no_cache

    return decorator
