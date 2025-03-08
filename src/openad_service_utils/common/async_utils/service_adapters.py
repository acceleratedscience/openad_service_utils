"""
Adapters for integrating the asynchronous inference system with existing services.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable, Tuple, List, Union
import copy
import json
import os
from functools import lru_cache

from .inference_manager import InferenceManager
from .request_queue import RequestPriority
from .config import AsyncInferenceConfig, get_default_config, RequestPriorityConfig

# Set up logging
logger = logging.getLogger(__name__)


def _map_priority(priority: str) -> RequestPriority:
    """Map a string priority to a RequestPriority enum value."""
    priority_map = {
        RequestPriorityConfig.LOW.value: RequestPriority.LOW,
        RequestPriorityConfig.NORMAL.value: RequestPriority.NORMAL,
        RequestPriorityConfig.HIGH.value: RequestPriority.HIGH,
        RequestPriorityConfig.CRITICAL.value: RequestPriority.CRITICAL,
    }
    return priority_map.get(priority.lower(), RequestPriority.NORMAL)


class PropertyServiceAdapter:
    """
    Adapter for integrating the asynchronous inference system with property services.
    
    This adapter provides a bridge between the existing property service API and
    the new asynchronous inference system.
    """
    
    def __init__(
        self,
        property_requestor,
        config: Optional[AsyncInferenceConfig] = None
    ):
        """
        Initialize the property service adapter.
        
        Args:
            property_requestor: The existing property service requestor
            config: Configuration for the asynchronous inference system
        """
        self.property_requestor = property_requestor
        self.config = config or get_default_config()
        
        # Initialize the inference manager
        self.inference_manager = InferenceManager(
            model_loader=self._load_property_model,
            model_inference=self._run_property_inference,
            max_workers=self.config.max_workers,
            max_models=self.config.max_models,
            max_memory_mb=self.config.max_memory_mb,
            eviction_strategy=self.config.eviction_strategy,
            result_ttl_hours=self.config.result_ttl_hours,
            result_dir=self.config.result_dir,
            cleanup_interval_seconds=self.config.cleanup_interval_seconds,
        )
        
        logger.info("Property service adapter initialized")
    
    def _load_property_model(self, request_data: Dict[str, Any]) -> Tuple[str, Callable[[], Any]]:
        """
        Load a property model based on the request data.
        
        Args:
            request_data: The request data
            
        Returns:
            A tuple of (model_id, load_function)
        """
        # Extract the model ID from the request data
        service_type = request_data.get("service_type", "")
        service_name = request_data.get("service_name", "")
        parameters = request_data.get("parameters", {})
        property_types = parameters.get("property_type", [])
        
        # Create a unique model ID based on the service type, name, and property types
        model_id = f"{service_type}_{service_name}_{'_'.join(property_types)}"
        
        # Additional parameters that might affect the model
        for param_name in ["algorithm_type", "domain", "algorithm_name", "algorithm_version", "algorithm_application"]:
            if param_name in parameters:
                model_id += f"_{param_name}_{parameters[param_name]}"
        
        # Define the load function
        def load_model():
            # This is a placeholder for the actual model loading logic
            # In reality, we would need to extract the model from the property_requestor
            # or load it directly using the appropriate APIs
            logger.info(f"Loading property model: {model_id}")
            
            # For now, we'll just return a dummy model that wraps the property_requestor
            # In a real implementation, we would load the actual model here
            return {
                "model_id": model_id,
                "service_type": service_type,
                "service_name": service_name,
                "parameters": copy.deepcopy(parameters),
            }
        
        return model_id, load_model
    
    def _run_property_inference(self, model: Any, request_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Run inference using a property model.
        
        Args:
            model: The model to use for inference
            request_data: The request data
            
        Returns:
            The inference results
        """
        logger.info(f"Running property inference with model: {model['model_id']}")
        
        try:
            # In a real implementation, we would use the model directly
            # For now, we'll just delegate to the property_requestor
            result = self.property_requestor.route_service(request_data)
            
            if result is None:
                raise ValueError("Property service returned None")
                
            return result
        except Exception as e:
            logger.error(f"Error running property inference: {e}")
            traceback.print_exc()
            raise
    
    def submit_async_request(
        self,
        request_data: Dict[str, Any],
        priority: str = "normal",
        timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit an asynchronous request for property inference.
        
        Args:
            request_data: The request data
            priority: Priority level for this request
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            A dictionary with the request ID
        """
        # Map the priority string to a RequestPriority enum value
        request_priority = _map_priority(priority)
        
        # Use the default timeout if not specified
        if timeout_seconds is None:
            timeout_seconds = self.config.default_request_timeout
        
        # Submit the request to the inference manager
        request_id = self.inference_manager.submit_request(
            request_data=request_data,
            priority=request_priority,
            timeout_seconds=timeout_seconds
        )
        
        return {"request_id": request_id}
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get the status of an asynchronous request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            A dictionary with request status information
        """
        status = self.inference_manager.get_request_status(request_id)
        
        if status is None:
            return {"error": "Request not found"}
            
        return status
    
    def cancel_request(self, request_id: str) -> Dict[str, Any]:
        """
        Cancel an asynchronous request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            A dictionary with the result of the cancellation
        """
        success = self.inference_manager.cancel_request(request_id)
        
        if success:
            return {"result": "Request canceled successfully"}
        else:
            return {"error": "Failed to cancel request"}
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current queue state.
        
        Returns:
            A dictionary with queue statistics
        """
        return self.inference_manager.get_queue_stats()
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the property service adapter.
        
        Args:
            wait: Whether to wait for all pending requests to complete
        """
        self.inference_manager.shutdown(wait=wait)


class GenerationServiceAdapter:
    """
    Adapter for integrating the asynchronous inference system with generation services.
    
    This adapter provides a bridge between the existing generation service API and
    the new asynchronous inference system.
    """
    
    def __init__(
        self,
        generation_requestor,
        config: Optional[AsyncInferenceConfig] = None
    ):
        """
        Initialize the generation service adapter.
        
        Args:
            generation_requestor: The existing generation service requestor
            config: Configuration for the asynchronous inference system
        """
        self.generation_requestor = generation_requestor
        self.config = config or get_default_config()
        
        # Initialize the inference manager
        self.inference_manager = InferenceManager(
            model_loader=self._load_generation_model,
            model_inference=self._run_generation_inference,
            max_workers=self.config.max_workers,
            max_models=self.config.max_models,
            max_memory_mb=self.config.max_memory_mb,
            eviction_strategy=self.config.eviction_strategy,
            result_ttl_hours=self.config.result_ttl_hours,
            result_dir=self.config.result_dir,
            cleanup_interval_seconds=self.config.cleanup_interval_seconds,
        )
        
        logger.info("Generation service adapter initialized")
    
    def _load_generation_model(self, request_data: Dict[str, Any]) -> Tuple[str, Callable[[], Any]]:
        """
        Load a generation model based on the request data.
        
        Args:
            request_data: The request data
            
        Returns:
            A tuple of (model_id, load_function)
        """
        # Extract the model ID from the request data
        service_type = request_data.get("service_type", "")
        service_name = request_data.get("service_name", "")
        parameters = request_data.get("parameters", {})
        property_types = parameters.get("property_type", [])
        
        # Create a unique model ID based on the service type, name, and property types
        model_id = f"{service_type}_{service_name}_{'_'.join(property_types)}"
        
        # Additional parameters that might affect the model
        for param_name in ["algorithm_type", "domain", "algorithm_name", "algorithm_version", "algorithm_application"]:
            if param_name in parameters:
                model_id += f"_{param_name}_{parameters[param_name]}"
        
        # Define the load function
        def load_model():
            # This is a placeholder for the actual model loading logic
            # In reality, we would need to extract the model from the generation_requestor
            # or load it directly using the appropriate APIs
            logger.info(f"Loading generation model: {model_id}")
            
            # For now, we'll just return a dummy model that wraps the generation_requestor
            # In a real implementation, we would load the actual model here
            return {
                "model_id": model_id,
                "service_type": service_type,
                "service_name": service_name,
                "parameters": copy.deepcopy(parameters),
            }
        
        return model_id, load_model
    
    def _run_generation_inference(self, model: Any, request_data: Dict[str, Any]) -> Any:
        """
        Run inference using a generation model.
        
        Args:
            model: The model to use for inference
            request_data: The request data
            
        Returns:
            The inference results
        """
        logger.info(f"Running generation inference with model: {model['model_id']}")
        
        try:
            # In a real implementation, we would use the model directly
            # For now, we'll just delegate to the generation_requestor
            result = self.generation_requestor.route_service(request_data)
            
            if result is None:
                raise ValueError("Generation service returned None")
                
            return result
        except Exception as e:
            logger.error(f"Error running generation inference: {e}")
            traceback.print_exc()
            raise
    
    def submit_async_request(
        self,
        request_data: Dict[str, Any],
        priority: str = "normal",
        timeout_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Submit an asynchronous request for generation inference.
        
        Args:
            request_data: The request data
            priority: Priority level for this request
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            A dictionary with the request ID
        """
        # Map the priority string to a RequestPriority enum value
        request_priority = _map_priority(priority)
        
        # Use the default timeout if not specified
        if timeout_seconds is None:
            timeout_seconds = self.config.default_request_timeout
        
        # Submit the request to the inference manager
        request_id = self.inference_manager.submit_request(
            request_data=request_data,
            priority=request_priority,
            timeout_seconds=timeout_seconds
        )
        
        return {"request_id": request_id}
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """
        Get the status of an asynchronous request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            A dictionary with request status information
        """
        status = self.inference_manager.get_request_status(request_id)
        
        if status is None:
            return {"error": "Request not found"}
            
        return status
    
    def cancel_request(self, request_id: str) -> Dict[str, Any]:
        """
        Cancel an asynchronous request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            A dictionary with the result of the cancellation
        """
        success = self.inference_manager.cancel_request(request_id)
        
        if success:
            return {"result": "Request canceled successfully"}
        else:
            return {"error": "Failed to cancel request"}
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current queue state.
        
        Returns:
            A dictionary with queue statistics
        """
        return self.inference_manager.get_queue_stats()
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the generation service adapter.
        
        Args:
            wait: Whether to wait for all pending requests to complete
        """
        self.inference_manager.shutdown(wait=wait)


# Global instances of the service adapters
_property_adapter = None
_generation_adapter = None


def get_property_adapter(property_requestor=None, config=None) -> PropertyServiceAdapter:
    """
    Get the global property service adapter instance.
    
    Args:
        property_requestor: The property service requestor (only used if the adapter hasn't been initialized yet)
        config: Configuration for the asynchronous inference system (only used if the adapter hasn't been initialized yet)
        
    Returns:
        The property service adapter
    """
    global _property_adapter
    
    if _property_adapter is None:
        if property_requestor is None:
            raise ValueError("Property requestor must be provided when initializing the adapter")
            
        _property_adapter = PropertyServiceAdapter(property_requestor, config)
        
    return _property_adapter


def get_generation_adapter(generation_requestor=None, config=None) -> GenerationServiceAdapter:
    """
    Get the global generation service adapter instance.
    
    Args:
        generation_requestor: The generation service requestor (only used if the adapter hasn't been initialized yet)
        config: Configuration for the asynchronous inference system (only used if the adapter hasn't been initialized yet)
        
    Returns:
        The generation service adapter
    """
    global _generation_adapter
    
    if _generation_adapter is None:
        if generation_requestor is None:
            raise ValueError("Generation requestor must be provided when initializing the adapter")
            
        _generation_adapter = GenerationServiceAdapter(generation_requestor, config)
        
    return _generation_adapter


def shutdown_adapters(wait: bool = True):
    """
    Shutdown all service adapters.
    
    Args:
        wait: Whether to wait for all pending requests to complete
    """
    global _property_adapter, _generation_adapter
    
    if _property_adapter is not None:
        _property_adapter.shutdown(wait=wait)
        _property_adapter = None
        
    if _generation_adapter is not None:
        _generation_adapter.shutdown(wait=wait)
        _generation_adapter = None
