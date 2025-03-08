"""
Request queue management for asynchronous model inference.
"""

import time
import uuid
import heapq
import threading
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)

class RequestStatus(Enum):
    """Status of a request in the queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELED = "canceled"


class RequestPriority(Enum):
    """Priority levels for requests."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass(order=True)
class QueuedRequest:
    """A request in the queue with priority handling."""
    # The sort_index is used by heapq for priority queue ordering
    sort_index: Tuple[int, float] = field(init=False, repr=False)
    
    # Request metadata
    request_id: str
    request_data: Dict[str, Any]
    priority: RequestPriority = RequestPriority.NORMAL
    status: RequestStatus = RequestStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout_seconds: Optional[int] = None
    result: Any = None
    error: Optional[str] = None
    
    def __post_init__(self):
        # Negative priority value ensures higher priority comes first
        # Then sort by creation time for requests with same priority
        self.sort_index = (-self.priority.value, self.created_at)
    
    @property
    def is_timed_out(self) -> bool:
        """Check if the request has timed out."""
        if self.timeout_seconds is None:
            return False
        
        if self.status == RequestStatus.COMPLETED or self.status == RequestStatus.FAILED:
            return False
            
        elapsed = time.time() - self.created_at
        return elapsed > self.timeout_seconds
    
    @property
    def elapsed_time(self) -> float:
        """Get the elapsed time for this request in seconds."""
        if self.completed_at:
            return self.completed_at - self.created_at
        return time.time() - self.created_at
    
    @property
    def processing_time(self) -> Optional[float]:
        """Get the processing time for this request in seconds."""
        if not self.started_at:
            return None
        
        if self.completed_at:
            return self.completed_at - self.started_at
        
        return time.time() - self.started_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the request to a dictionary for API responses."""
        result = {
            "request_id": self.request_id,
            "status": self.status.value,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "elapsed_time": f"{self.elapsed_time:.2f}s",
        }
        
        if self.started_at:
            result["started_at"] = datetime.fromtimestamp(self.started_at).isoformat()
            
        if self.processing_time is not None:
            result["processing_time"] = f"{self.processing_time:.2f}s"
            
        if self.completed_at:
            result["completed_at"] = datetime.fromtimestamp(self.completed_at).isoformat()
            
        if self.status == RequestStatus.COMPLETED:
            result["result"] = self.result
            
        if self.status == RequestStatus.FAILED:
            result["error"] = self.error
            
        return result


class RequestQueue:
    """
    A priority queue for managing asynchronous model inference requests.
    
    Features:
    - Priority-based scheduling
    - Request timeout handling
    - Status tracking
    - Concurrency control
    """
    
    def __init__(self, max_concurrent_requests: int = 10):
        """
        Initialize the request queue.
        
        Args:
            max_concurrent_requests: Maximum number of requests that can be processed concurrently
        """
        self._queue = []  # Priority queue of pending requests
        self._requests = {}  # Map of request_id to QueuedRequest
        self._processing = set()  # Set of request_ids currently being processed
        self._lock = threading.RLock()  # Lock for thread safety
        self._max_concurrent = max_concurrent_requests
        self._condition = threading.Condition(self._lock)  # For wait/notify
    
    def add_request(
        self, 
        request_data: Dict[str, Any], 
        priority: RequestPriority = RequestPriority.NORMAL,
        timeout_seconds: Optional[int] = None
    ) -> str:
        """
        Add a request to the queue.
        
        Args:
            request_data: The request data to be processed
            priority: Priority level for this request
            timeout_seconds: Optional timeout in seconds
            
        Returns:
            request_id: Unique identifier for the request
        """
        request_id = str(uuid.uuid4())
        
        with self._lock:
            request = QueuedRequest(
                request_id=request_id,
                request_data=request_data,
                priority=priority,
                timeout_seconds=timeout_seconds
            )
            
            self._requests[request_id] = request
            heapq.heappush(self._queue, request)
            
            # Notify any waiting threads that a new request is available
            self._condition.notify()
            
        logger.info(f"Added request {request_id} with priority {priority.name}")
        return request_id
    
    def get_request_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            A dictionary with request status information or None if not found
        """
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                return None
                
            # Check for timeout
            if request.is_timed_out and request.status == RequestStatus.PENDING:
                request.status = RequestStatus.TIMEOUT
                request.error = "Request timed out while waiting in queue"
                
            return request.to_dict()
    
    def get_next_request(self) -> Optional[QueuedRequest]:
        """
        Get the next request to process based on priority.
        
        Returns:
            The next request to process or None if the queue is empty or at capacity
        """
        with self._lock:
            # Wait until we have capacity and there are requests in the queue
            while len(self._processing) >= self._max_concurrent or not self._queue:
                self._condition.wait(timeout=1.0)  # Wait with timeout to check for request timeouts
                
                # Check for timeouts in the queue
                self._check_timeouts()
                
                # If we still don't have capacity or requests, return None
                if len(self._processing) >= self._max_concurrent or not self._queue:
                    return None
            
            # Get the highest priority request
            request = heapq.heappop(self._queue)
            
            # Check if it has timed out
            if request.is_timed_out:
                request.status = RequestStatus.TIMEOUT
                request.error = "Request timed out while waiting in queue"
                return None
                
            # Mark as processing
            request.status = RequestStatus.PROCESSING
            request.started_at = time.time()
            self._processing.add(request.request_id)
            
            logger.info(f"Processing request {request.request_id}")
            return request
    
    def complete_request(self, request_id: str, result: Any = None, error: Optional[str] = None):
        """
        Mark a request as completed or failed.
        
        Args:
            request_id: The unique identifier for the request
            result: The result of the request (if successful)
            error: Error message (if failed)
        """
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                logger.warning(f"Attempted to complete unknown request {request_id}")
                return
                
            request.completed_at = time.time()
            
            if error:
                request.status = RequestStatus.FAILED
                request.error = error
                logger.error(f"Request {request_id} failed: {error}")
            else:
                request.status = RequestStatus.COMPLETED
                request.result = result
                logger.info(f"Request {request_id} completed successfully")
                
            # Remove from processing set
            self._processing.discard(request_id)
            
            # Notify waiting threads that capacity is available
            self._condition.notify()
    
    def cancel_request(self, request_id: str) -> bool:
        """
        Cancel a pending request.
        
        Args:
            request_id: The unique identifier for the request
            
        Returns:
            True if the request was canceled, False if it couldn't be canceled
        """
        with self._lock:
            request = self._requests.get(request_id)
            if not request:
                return False
                
            # Can only cancel pending requests
            if request.status != RequestStatus.PENDING:
                return False
                
            # Mark as canceled
            request.status = RequestStatus.CANCELED
            request.completed_at = time.time()
            request.error = "Request canceled by user"
            
            # Need to rebuild the queue without this request
            # This is inefficient but cancellations should be rare
            self._queue = [r for r in self._queue if r.request_id != request_id]
            heapq.heapify(self._queue)
            
            logger.info(f"Canceled request {request_id}")
            return True
    
    def _check_timeouts(self):
        """Check for and handle timed out requests in the queue."""
        timed_out = []
        
        # Find timed out requests
        for i, request in enumerate(self._queue):
            if request.is_timed_out:
                timed_out.append(i)
                
        # Handle timed out requests (in reverse order to maintain indices)
        for i in reversed(timed_out):
            request = self._queue.pop(i)
            request.status = RequestStatus.TIMEOUT
            request.error = "Request timed out while waiting in queue"
            request.completed_at = time.time()
            
            logger.warning(f"Request {request.request_id} timed out in queue")
            
        # Reheapify if we removed any requests
        if timed_out:
            heapq.heapify(self._queue)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current queue state.
        
        Returns:
            A dictionary with queue statistics
        """
        with self._lock:
            pending_count = len(self._queue)
            processing_count = len(self._processing)
            
            # Count requests by status
            status_counts = {status.value: 0 for status in RequestStatus}
            for request in self._requests.values():
                status_counts[request.status.value] += 1
                
            # Count requests by priority
            priority_counts = {priority.name: 0 for priority in RequestPriority}
            for request in self._queue:
                priority_counts[request.priority.name] += 1
                
            return {
                "queue_length": pending_count,
                "processing_count": processing_count,
                "total_requests": len(self._requests),
                "status_counts": status_counts,
                "priority_counts": priority_counts,
                "max_concurrent_requests": self._max_concurrent
            }
    
    def cleanup_completed_requests(self, max_age_hours: int = 24):
        """
        Remove old completed, failed, or canceled requests from memory.
        
        Args:
            max_age_hours: Maximum age in hours for completed requests to be kept
        """
        with self._lock:
            cutoff_time = time.time() - (max_age_hours * 3600)
            to_remove = []
            
            for request_id, request in self._requests.items():
                if (request.status in (RequestStatus.COMPLETED, RequestStatus.FAILED, 
                                      RequestStatus.CANCELED, RequestStatus.TIMEOUT) and
                    request.completed_at and request.completed_at < cutoff_time):
                    to_remove.append(request_id)
                    
            for request_id in to_remove:
                del self._requests[request_id]
                
            logger.info(f"Cleaned up {len(to_remove)} old completed requests")
