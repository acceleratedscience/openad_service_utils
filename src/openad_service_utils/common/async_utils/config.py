"""
Configuration for the asynchronous inference system.
"""

import os
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator

from .resource_manager import EvictionStrategy


class RequestPriorityConfig(str, Enum):
    """Priority levels for requests in configuration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class AsyncInferenceConfig(BaseModel):
    """Configuration for the asynchronous inference system."""
    
    # Request queue settings
    max_queue_size: int = Field(
        default=1000,
        description="Maximum number of requests in the queue",
        ge=1
    )
    
    default_request_timeout: Optional[int] = Field(
        default=None,
        description="Default timeout for requests in seconds (None for no timeout)"
    )
    
    default_request_priority: RequestPriorityConfig = Field(
        default=RequestPriorityConfig.NORMAL,
        description="Default priority for requests"
    )
    
    # Worker settings
    max_workers: int = Field(
        default=4,
        description="Maximum number of worker threads for processing requests",
        ge=1
    )
    
    # Model resource management settings
    max_models: int = Field(
        default=5,
        description="Maximum number of models to keep loaded simultaneously",
        ge=1
    )
    
    max_memory_mb: Optional[float] = Field(
        default=None,
        description="Maximum memory usage in MB (None for no limit)"
    )
    
    eviction_strategy: str = Field(
        default=EvictionStrategy.LRU.value,
        description="Strategy to use when evicting models"
    )
    
    memory_headroom_mb: float = Field(
        default=1000.0,
        description="Amount of memory to keep free in MB",
        ge=0
    )
    
    # Result storage settings
    result_ttl_hours: int = Field(
        default=24,
        description="Time to live for results in hours",
        ge=1
    )
    
    result_dir: str = Field(
        default="/tmp/openad_async_results",
        description="Directory to store results"
    )
    
    cleanup_interval_seconds: int = Field(
        default=3600,
        description="Interval for cleaning up old results in seconds",
        ge=60
    )
    
    # Model-specific settings
    model_specific_settings: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Model-specific settings, keyed by model ID"
    )
    
    @validator("eviction_strategy")
    def validate_eviction_strategy(cls, v):
        """Validate that the eviction strategy is valid."""
        valid_strategies = [strategy.value for strategy in EvictionStrategy]
        if v not in valid_strategies:
            raise ValueError(f"Invalid eviction strategy: {v}. Valid strategies: {valid_strategies}")
        return v
    
    @validator("result_dir")
    def validate_result_dir(cls, v):
        """Validate that the result directory exists or can be created."""
        os.makedirs(v, exist_ok=True)
        return v
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "OPENAD_ASYNC_"
        case_sensitive = False


def get_default_config() -> AsyncInferenceConfig:
    """Get the default configuration for the asynchronous inference system."""
    return AsyncInferenceConfig()


def get_config_from_env() -> AsyncInferenceConfig:
    """Get the configuration from environment variables."""
    return AsyncInferenceConfig.parse_obj({})


def get_config_from_file(file_path: str) -> AsyncInferenceConfig:
    """
    Get the configuration from a file.
    
    Args:
        file_path: Path to the configuration file (JSON or YAML)
        
    Returns:
        The configuration
    """
    import json
    import yaml
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    with open(file_path, "r") as f:
        if file_path.endswith(".json"):
            config_dict = json.load(f)
        elif file_path.endswith((".yaml", ".yml")):
            config_dict = yaml.safe_load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {file_path}")
    
    return AsyncInferenceConfig.parse_obj(config_dict)
