"""
Asynchronous inference manager for handling model inference requests.
"""

import time
import logging
import threading
import traceback
from typing import Dict, List, Any, Optional, Callable, Tuple, TypeVar, Generic, Union
from concurrent.futures import ThreadPoolExecutor
import queue
import uuid
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

from .request_queue import RequestQueue, RequestStatus, RequestPriority, QueuedRequest
from .resource_manager import ModelResourceManager, EvictionStrategy

# Set up logging
logger = logging.getLogger(__name__)

# Type for model and result
T = TypeVar('T')  # Model type
R = TypeVar('R')  # Result type


class InferenceManager(Generic[T, R]):
    """
    Manager for asynchronous model inference requests.
    
    This class ties together the request queue and resource manager to provide
    a complete solution for handling asynchronous model inference requests.
    
    Features:
    - Accepts and queues inference requests
    - Manages model loading and unloading
    - Processes requests in priority order
    - Provides status updates for in-progress requests
    - Handles timeouts and errors
    - Implements model caching
    """
    
    def __init__(
        self,
        model_loader: Callable[[Dict[str, Any]], Tuple[str, Callable[[], T]]],
        model_inference: Callable[[T, Dict[str, Any]], R],
        max_workers: int = 4,
        max_queue_size: int = 100,
        max_models: int = 5,
        max_memory_mb: Optional[float] = None,
        eviction_strategy: EvictionStrategy = EvictionStrategy.LRU,
        result_ttl_hours: int = 24,
        result_dir: str = "/tmp/openad_async_results",
        cleanup_interval_seconds: int = 3600,  # 1 hour
    ):
        """
        Initialize the inference manager.
        
        Args:
            model_loader: Function that takes request parameters and returns a tuple of
                         (model_id, load_function)
            model_inference: Function that takes a model and request parameters and
                            returns the inference result
            max_workers: Maximum number of worker threads for processing requests
            max_queue_size: Maximum size of the request queue
            max_models: Maximum number of models to keep loaded simultaneously
            max_memory_mb: Maximum memory usage in MB (None for no limit)
            eviction_strategy: Strategy to use when evicting models
            result_ttl_hours: Time to live for results in hours
            result_dir: Directory to store results
            cleanup_interval_seconds: Interval for cleaning up old results
        """
        self.model_loader = model_loader
        self.model_inference = model_inference
        self.max_workers = max_workers
        
        # Initialize the request queue
        self.request_queue = RequestQueue(max_concurrent_requests=max_workers)
        
        # Initialize the resource manager
        self.resource_manager = ModelResourceManager[T](
            max_models=max_models,
            max_memory_mb=max_memory_mb,
            eviction_strategy=eviction_strategy
        )
        
        # Thread pool for processing requests
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # For storing results
        self.result_ttl = timedelta(hours=result_ttl_hours)
        self.result_dir = result_dir
        os.makedirs(self.result_dir, exist_ok=True)
        
        # Start the worker threads
        self.shutdown_event = threading.Event()
        self.worker_threads = []
        for _ in range(max_workers):
            thread = threading.Thread(target=self._worker_loop, daemon=True)
            thread.start()
            self.worker_threads.append(thread)
        
        # Start the cleanup thread
        self.cleanup_interval = cleanup_interval_seconds
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        
        logger.info(f"Inference manager initialized with {max_workers} workers")
    
    def submit_request(
        self,
        request_data: Dict[str, Any],
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout_seconds: Optional[int] = None
    ) -> str:
        """
        Submit a request for asynchronous processing.
        
        Args:
            request_data: The request data to be processed
            priority: Priority level for this request
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            request_id: Unique identifier for the request
        """
        request_id = self.request_queue.add_request(
            request_data=request_data,
            priority=priority,
            timeout_seconds=timeout_seconds
        )
        
        logger.info(f"Submitted request {request_id} with priority {priority.name}")
        return request_id
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            A dictionary with request status information or None if not found
        """
        # First check the in-memory queue
        status = self.request_queue.get_request_status(request_id)
        if status:
            return status
        
        # If not found in memory, check the result files
        result_path = os.path.join(self.result_dir, f"{request_id}.json")
        if os.path.exists(result_path):
            try:
                with open(result_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading result file for request {request_id}: {e}")
                return None
        
        return None
    
    def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            True if the request was canceled, False if it couldn't be canceled
        """
        return self.request_queue.cancel_request(request_id)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current queue state.
        
        Returns:
            A dictionary with queue statistics
        """
        queue_stats = self.request_queue.get_queue_stats()
        model_stats = self.resource_manager.get_model_stats()
        
        return {
            "queue": queue_stats,
            "models": model_stats,
            "workers": self.max_workers,
        }
    
    def shutdown(self, wait: bool = True):
        """
        Shutdown the inference manager.
        
        Args:
            wait: Whether to wait for all pending requests to complete
        """
        logger.info("Shutting down inference manager")
        self.shutdown_event.set()
        
        if wait:
            for thread in self.worker_threads:
                thread.join()
            
            self.cleanup_thread.join()
        
        self.executor.shutdown(wait=wait)
        self.resource_manager.clear_all_models()
        
        logger.info("Inference manager shutdown complete")
    
    def _worker_loop(self):
        """Worker thread loop for processing requests."""
        while not self.shutdown_event.is_set():
            try:
                # Get the next request from the queue
                request = self.request_queue.get_next_request()
                if not request:
                    # No request available, wait a bit
                    time.sleep(0.1)
                    continue
                
                # Process the request
                self._process_request(request)
            except Exception as e:
                logger.error(f"Error in worker thread: {e}")
                traceback.print_exc()
    
    def _process_request(self, request: QueuedRequest):
        """
        Process a single request.
        
        Args:
            request: The request to process
        """
        logger.info(f"Processing request {request.request_id}")
        
        try:
            # Get the model ID and loader function
            model_id, load_func = self.model_loader(request.request_data)
            logger.info(f"Request {request.request_id} requires model {model_id}")
            
            # Get the model from the resource manager
            model, error = self.resource_manager.get_model(
                model_id=model_id,
                load_func=load_func,
                block=True,
                timeout=request.timeout_seconds
            )
            
            if error:
                # Model loading failed
                self.request_queue.complete_request(
                    request_id=request.request_id,
                    error=f"Model loading failed: {error}"
                )
                self._save_result(request.request_id, None, error)
                return
            
            # Run inference
            try:
                result = self.model_inference(model, request.request_data)
                
                # Mark the request as completed
                self.request_queue.complete_request(
                    request_id=request.request_id,
                    result=result
                )
                
                # Save the result
                self._save_result(request.request_id, result)
                
                logger.info(f"Request {request.request_id} completed successfully")
            except Exception as e:
                # Inference failed
                error_msg = f"Inference failed: {str(e)}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                
                self.request_queue.complete_request(
                    request_id=request.request_id,
                    error=error_msg
                )
                
                self._save_result(request.request_id, None, error_msg)
        except Exception as e:
            # Request processing failed
            error_msg = f"Request processing failed: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            self.request_queue.complete_request(
                request_id=request.request_id,
                error=error_msg
            )
            
            self._save_result(request.request_id, None, error_msg)
    
    def _save_result(self, request_id: str, result: Optional[R] = None, error: Optional[str] = None):
        """
        Save the result of a request to a file.
        
        Args:
            request_id: The unique identifier for the request
            result: The result of the request (if successful)
            error: Error message (if failed)
        """
        result_path = os.path.join(self.result_dir, f"{request_id}.json")
        
        # Get the status from the queue
        status = self.request_queue.get_request_status(request_id)
        if not status:
            # This shouldn't happen, but just in case
            status = {
                "request_id": request_id,
                "status": "unknown",
                "created_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
            }
        
        # Add expiration time
        status["expires_at"] = (datetime.now() + self.result_ttl).isoformat()
        
        try:
            with open(result_path, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving result for request {request_id}: {e}")
    
    def _cleanup_loop(self):
        """Cleanup thread loop for removing old results and completed requests."""
        while not self.shutdown_event.is_set():
            try:
                # Clean up old results
                self._cleanup_old_results()
                
                # Clean up completed requests from the queue
                self.request_queue.cleanup_completed_requests()
                
                # Wait for the next cleanup interval
                self.shutdown_event.wait(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                traceback.print_exc()
                
                # Wait a bit before trying again
                time.sleep(60)
    
    def _cleanup_old_results(self):
        """Clean up old result files."""
        now = datetime.now()
        count = 0
        
        for path in Path(self.result_dir).glob("*.json"):
            try:
                # Check if the file is older than the TTL
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if now - mtime > self.result_ttl:
                    # Delete the file
                    path.unlink()
                    count += 1
                else:
                    # Check if the result has expired based on the expires_at field
                    try:
                        with open(path, 'r') as f:
                            data = json.load(f)
                            if "expires_at" in data:
                                expires_at = datetime.fromisoformat(data["expires_at"])
                                if now > expires_at:
                                    # Delete the file
                                    path.unlink()
                                    count += 1
                    except Exception:
                        # If we can't read the file, just use the mtime check
                        pass
            except Exception as e:
                logger.warning(f"Error cleaning up result file {path}: {e}")
        
        if count > 0:
            logger.info(f"Cleaned up {count} old result files")
