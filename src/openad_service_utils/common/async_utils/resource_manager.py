"""
Resource management for model inference, including model loading, memory management, and eviction strategies.
"""

import os
import time
import logging
import threading
import weakref
from typing import Dict, List, Set, Any, Optional, Callable, Tuple, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import gc

# Set up logging
logger = logging.getLogger(__name__)

# Try to import torch for GPU memory management
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.info("PyTorch not available, GPU memory management will be disabled")


class EvictionStrategy(Enum):
    """Strategies for model eviction when memory constraints are reached."""
    LRU = "least_recently_used"  # Evict the least recently used model
    LFU = "least_frequently_used"  # Evict the least frequently used model
    SIZE = "largest_size"  # Evict the largest model


@dataclass
class ModelInfo:
    """Information about a loaded model."""
    model_id: str  # Unique identifier for the model
    model: Any  # The actual model object
    size_mb: float  # Estimated size in MB
    load_time: float = field(default_factory=time.time)  # When the model was loaded
    last_used: float = field(default_factory=time.time)  # When the model was last used
    use_count: int = 0  # How many times the model has been used
    is_loading: bool = True  # Whether the model is currently being loaded
    loading_thread: Optional[threading.Thread] = None  # Thread loading the model
    
    def mark_used(self):
        """Mark the model as used."""
        self.last_used = time.time()
        self.use_count += 1


T = TypeVar('T')  # Type for the model


class ModelResourceManager(Generic[T]):
    """
    Manages model resources, including loading, caching, and memory management.
    
    Features:
    - Limits the number of simultaneously loaded models
    - Implements model eviction strategies
    - Tracks model usage statistics
    - Provides memory usage monitoring
    """
    
    def __init__(
        self,
        max_models: int = 5,
        max_memory_mb: Optional[float] = None,
        eviction_strategy: EvictionStrategy = EvictionStrategy.LRU,
        memory_headroom_mb: float = 1000.0,  # 1GB headroom
    ):
        """
        Initialize the model resource manager.
        
        Args:
            max_models: Maximum number of models to keep loaded simultaneously
            max_memory_mb: Maximum memory usage in MB (None for no limit)
            eviction_strategy: Strategy to use when evicting models
            memory_headroom_mb: Amount of memory to keep free in MB
        """
        self._models: Dict[str, ModelInfo] = {}
        self._loading_models: Set[str] = set()
        self._lock = threading.RLock()
        self._max_models = max_models
        self._max_memory_mb = max_memory_mb
        self._eviction_strategy = eviction_strategy
        self._memory_headroom_mb = memory_headroom_mb
        
        # For tracking memory usage
        self._last_memory_check = 0
        self._memory_check_interval = 5.0  # seconds
    
    def get_model(
        self,
        model_id: str,
        load_func: Callable[[], T],
        size_estimator: Callable[[T], float] = None,
        estimated_size_mb: float = 500.0,  # Default estimate if size_estimator not provided
        block: bool = True,
        timeout: Optional[float] = None,
    ) -> Tuple[Optional[T], Optional[str]]:
        """
        Get a model, loading it if necessary.
        
        Args:
            model_id: Unique identifier for the model
            load_func: Function to call to load the model
            size_estimator: Function to estimate the size of the model in MB
            estimated_size_mb: Estimated size of the model in MB if size_estimator not provided
            block: Whether to block until the model is loaded
            timeout: Maximum time to wait for the model to load
            
        Returns:
            Tuple of (model, error_message)
            - If successful, (model, None)
            - If error, (None, error_message)
        """
        with self._lock:
            # Check if model is already loaded
            if model_id in self._models:
                model_info = self._models[model_id]
                
                # If the model is still loading
                if model_info.is_loading:
                    if not block:
                        return None, "Model is still loading"
                    
                    # Release the lock while waiting
                    self._lock.release()
                    try:
                        if timeout:
                            model_info.loading_thread.join(timeout)
                            if model_info.is_loading:
                                return None, "Timeout waiting for model to load"
                        else:
                            model_info.loading_thread.join()
                    finally:
                        self._lock.acquire()
                    
                    # Check if loading failed
                    if model_id not in self._models:
                        return None, "Model loading failed"
                
                # Mark the model as used
                model_info.mark_used()
                return model_info.model, None
            
            # Check if we need to evict models
            self._check_and_evict_models(estimated_size_mb)
            
            # Start loading the model
            model_info = ModelInfo(
                model_id=model_id,
                model=None,
                size_mb=estimated_size_mb,
                is_loading=True
            )
            self._models[model_id] = model_info
            self._loading_models.add(model_id)
            
            # Define the loading function
            def _load_model():
                try:
                    # Load the model
                    model = load_func()
                    
                    # Estimate the size if a size estimator is provided
                    if size_estimator and model is not None:
                        try:
                            size_mb = size_estimator(model)
                        except Exception as e:
                            logger.warning(f"Error estimating model size: {e}")
                            size_mb = estimated_size_mb
                    else:
                        size_mb = estimated_size_mb
                    
                    with self._lock:
                        if model_id in self._models:
                            # Update the model info
                            self._models[model_id].model = model
                            self._models[model_id].size_mb = size_mb
                            self._models[model_id].is_loading = False
                            self._loading_models.discard(model_id)
                            logger.info(f"Model {model_id} loaded successfully, size: {size_mb:.2f} MB")
                        else:
                            # Model was evicted while loading
                            logger.warning(f"Model {model_id} was evicted while loading")
                            # Clean up the model
                            del model
                            gc.collect()
                            if TORCH_AVAILABLE and torch.cuda.is_available():
                                torch.cuda.empty_cache()
                except Exception as e:
                    logger.error(f"Error loading model {model_id}: {e}")
                    with self._lock:
                        if model_id in self._models:
                            del self._models[model_id]
                        self._loading_models.discard(model_id)
            
            # Start the loading thread
            loading_thread = threading.Thread(target=_load_model, daemon=True)
            model_info.loading_thread = loading_thread
            loading_thread.start()
            
            if not block:
                return None, "Model is loading"
            
            # Release the lock while waiting
            self._lock.release()
            try:
                if timeout:
                    loading_thread.join(timeout)
                    if model_id not in self._models or self._models[model_id].is_loading:
                        return None, "Timeout waiting for model to load"
                else:
                    loading_thread.join()
            finally:
                self._lock.acquire()
            
            # Check if loading failed
            if model_id not in self._models:
                return None, "Model loading failed"
            
            model_info = self._models[model_id]
            if model_info.is_loading:
                return None, "Model is still loading"
            
            # Mark the model as used
            model_info.mark_used()
            return model_info.model, None
    
    def release_model(self, model_id: str):
        """
        Release a model, allowing it to be evicted if necessary.
        
        Args:
            model_id: Unique identifier for the model
        """
        # This is a no-op in this implementation, as models are automatically
        # evicted based on the eviction strategy. But it could be extended
        # to support reference counting or other release strategies.
        pass
    
    def evict_model(self, model_id: str) -> bool:
        """
        Explicitly evict a model from memory.
        
        Args:
            model_id: Unique identifier for the model
            
        Returns:
            True if the model was evicted, False if it wasn't loaded
        """
        with self._lock:
            if model_id not in self._models:
                return False
            
            model_info = self._models[model_id]
            
            # If the model is still loading, we can't safely evict it
            if model_info.is_loading:
                logger.warning(f"Cannot evict model {model_id} while it's loading")
                return False
            
            # Clean up the model
            model = model_info.model
            del self._models[model_id]
            
            # Force garbage collection
            del model
            gc.collect()
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Evicted model {model_id}")
            return True
    
    def _check_and_evict_models(self, new_model_size_mb: float = 0.0):
        """
        Check if we need to evict models and do so if necessary.
        
        Args:
            new_model_size_mb: Size of a new model that's about to be loaded
        """
        # Check if we're over the model count limit
        loaded_models = len(self._models) - len(self._loading_models)
        if loaded_models >= self._max_models:
            self._evict_models(1)
        
        # Check if we're over the memory limit
        if self._max_memory_mb is not None:
            current_memory = self._get_current_memory_usage()
            if current_memory + new_model_size_mb > self._max_memory_mb:
                # Calculate how many models to evict
                memory_to_free = current_memory + new_model_size_mb - self._max_memory_mb + self._memory_headroom_mb
                self._evict_models_by_memory(memory_to_free)
    
    def _evict_models(self, count: int = 1):
        """
        Evict a specified number of models based on the eviction strategy.
        
        Args:
            count: Number of models to evict
        """
        if not self._models:
            return
        
        # Get models that are not currently loading
        available_models = [
            model_id for model_id, info in self._models.items() 
            if not info.is_loading
        ]
        
        if not available_models:
            logger.warning("No models available for eviction")
            return
        
        # Sort models based on the eviction strategy
        if self._eviction_strategy == EvictionStrategy.LRU:
            # Sort by last used time (oldest first)
            sorted_models = sorted(
                available_models,
                key=lambda mid: self._models[mid].last_used
            )
        elif self._eviction_strategy == EvictionStrategy.LFU:
            # Sort by use count (least used first)
            sorted_models = sorted(
                available_models,
                key=lambda mid: self._models[mid].use_count
            )
        elif self._eviction_strategy == EvictionStrategy.SIZE:
            # Sort by size (largest first)
            sorted_models = sorted(
                available_models,
                key=lambda mid: -self._models[mid].size_mb
            )
        else:
            # Default to LRU
            sorted_models = sorted(
                available_models,
                key=lambda mid: self._models[mid].last_used
            )
        
        # Evict the models
        for i in range(min(count, len(sorted_models))):
            model_id = sorted_models[i]
            self.evict_model(model_id)
    
    def _evict_models_by_memory(self, memory_mb: float):
        """
        Evict models to free up a specified amount of memory.
        
        Args:
            memory_mb: Amount of memory to free in MB
        """
        if not self._models:
            return
        
        # Get models that are not currently loading
        available_models = [
            (model_id, info) for model_id, info in self._models.items() 
            if not info.is_loading
        ]
        
        if not available_models:
            logger.warning("No models available for eviction")
            return
        
        # Sort models based on the eviction strategy
        if self._eviction_strategy == EvictionStrategy.LRU:
            # Sort by last used time (oldest first)
            sorted_models = sorted(
                available_models,
                key=lambda item: item[1].last_used
            )
        elif self._eviction_strategy == EvictionStrategy.LFU:
            # Sort by use count (least used first)
            sorted_models = sorted(
                available_models,
                key=lambda item: item[1].use_count
            )
        elif self._eviction_strategy == EvictionStrategy.SIZE:
            # Sort by size (largest first)
            sorted_models = sorted(
                available_models,
                key=lambda item: -item[1].size_mb
            )
        else:
            # Default to LRU
            sorted_models = sorted(
                available_models,
                key=lambda item: item[1].last_used
            )
        
        # Evict models until we've freed enough memory
        memory_freed = 0.0
        for model_id, info in sorted_models:
            if memory_freed >= memory_mb:
                break
            
            memory_freed += info.size_mb
            self.evict_model(model_id)
    
    def _get_current_memory_usage(self) -> float:
        """
        Get the current memory usage of all loaded models in MB.
        
        Returns:
            Total memory usage in MB
        """
        # Only check memory usage periodically to avoid overhead
        current_time = time.time()
        if current_time - self._last_memory_check < self._memory_check_interval:
            # Sum up the estimated sizes of all loaded models
            return sum(
                info.size_mb for info in self._models.values()
                if not info.is_loading
            )
        
        self._last_memory_check = current_time
        
        # For more accurate memory usage, we could use psutil or other libraries
        # But for now, we'll just sum up the estimated sizes
        memory_usage = sum(
            info.size_mb for info in self._models.values()
            if not info.is_loading
        )
        
        # If PyTorch is available, we can get GPU memory usage
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                # Get GPU memory usage in bytes and convert to MB
                gpu_memory = torch.cuda.memory_allocated() / (1024 * 1024)
                logger.debug(f"Current GPU memory usage: {gpu_memory:.2f} MB")
            except Exception as e:
                logger.warning(f"Error getting GPU memory usage: {e}")
        
        return memory_usage
    
    def get_model_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current model cache.
        
        Returns:
            A dictionary with model statistics
        """
        with self._lock:
            loaded_count = len(self._models) - len(self._loading_models)
            loading_count = len(self._loading_models)
            
            # Calculate total memory usage
            memory_usage = self._get_current_memory_usage()
            
            # Get stats for each model
            model_stats = {}
            for model_id, info in self._models.items():
                model_stats[model_id] = {
                    "size_mb": info.size_mb,
                    "load_time": datetime.fromtimestamp(info.load_time).isoformat(),
                    "last_used": datetime.fromtimestamp(info.last_used).isoformat(),
                    "use_count": info.use_count,
                    "is_loading": info.is_loading,
                }
            
            return {
                "loaded_models": loaded_count,
                "loading_models": loading_count,
                "total_memory_mb": memory_usage,
                "max_models": self._max_models,
                "max_memory_mb": self._max_memory_mb,
                "eviction_strategy": self._eviction_strategy.value,
                "models": model_stats,
            }
    
    def clear_all_models(self):
        """Clear all models from the cache."""
        with self._lock:
            # Get a list of models that are not loading
            to_evict = [
                model_id for model_id, info in self._models.items()
                if not info.is_loading
            ]
            
            # Evict each model
            for model_id in to_evict:
                self.evict_model(model_id)
            
            # Force garbage collection
            gc.collect()
            if TORCH_AVAILABLE and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Cleared {len(to_evict)} models from cache")


# Add datetime import for the get_model_stats method
from datetime import datetime
