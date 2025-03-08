"""
Tests for the asynchronous inference system.
"""

import unittest
import tempfile
import os
import time
import threading
import json
from unittest.mock import MagicMock, patch

from openad_service_utils.common.async_utils.request_queue import (
    RequestQueue, RequestStatus, RequestPriority, QueuedRequest
)
from openad_service_utils.common.async_utils.resource_manager import (
    ModelResourceManager, EvictionStrategy
)
from openad_service_utils.common.async_utils.inference_manager import (
    InferenceManager
)
from openad_service_utils.common.async_utils.config import (
    AsyncInferenceConfig, get_default_config
)


class TestRequestQueue(unittest.TestCase):
    """Tests for the RequestQueue class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.queue = RequestQueue(max_concurrent_requests=2)
    
    def test_add_request(self):
        """Test adding a request to the queue."""
        request_id = self.queue.add_request(
            request_data={"test": "data"},
            priority=RequestPriority.NORMAL
        )
        
        self.assertIsNotNone(request_id)
        status = self.queue.get_request_status(request_id)
        self.assertEqual(status["status"], RequestStatus.PENDING.value)
    
    def test_get_next_request(self):
        """Test getting the next request from the queue."""
        # Add a request
        request_id = self.queue.add_request(
            request_data={"test": "data"},
            priority=RequestPriority.NORMAL
        )
        
        # Get the next request
        request = self.queue.get_next_request()
        
        self.assertIsNotNone(request)
        self.assertEqual(request.request_id, request_id)
        self.assertEqual(request.status, RequestStatus.PROCESSING)
    
    def test_complete_request(self):
        """Test completing a request."""
        # Add a request
        request_id = self.queue.add_request(
            request_data={"test": "data"},
            priority=RequestPriority.NORMAL
        )
        
        # Get the next request
        request = self.queue.get_next_request()
        
        # Complete the request
        self.queue.complete_request(
            request_id=request_id,
            result={"result": "success"}
        )
        
        # Check the status
        status = self.queue.get_request_status(request_id)
        self.assertEqual(status["status"], RequestStatus.COMPLETED.value)
        self.assertEqual(status["result"], {"result": "success"})
    
    def test_cancel_request(self):
        """Test canceling a request."""
        # Add a request
        request_id = self.queue.add_request(
            request_data={"test": "data"},
            priority=RequestPriority.NORMAL
        )
        
        # Cancel the request
        success = self.queue.cancel_request(request_id)
        
        self.assertTrue(success)
        status = self.queue.get_request_status(request_id)
        self.assertEqual(status["status"], RequestStatus.CANCELED.value)
    
    def test_priority_ordering(self):
        """Test that requests are processed in priority order."""
        # Add requests with different priorities
        low_id = self.queue.add_request(
            request_data={"priority": "low"},
            priority=RequestPriority.LOW
        )
        
        high_id = self.queue.add_request(
            request_data={"priority": "high"},
            priority=RequestPriority.HIGH
        )
        
        normal_id = self.queue.add_request(
            request_data={"priority": "normal"},
            priority=RequestPriority.NORMAL
        )
        
        # Get the next request (should be high priority)
        request = self.queue.get_next_request()
        self.assertEqual(request.request_id, high_id)
        
        # Complete the request
        self.queue.complete_request(request_id=high_id, result=None)
        
        # Get the next request (should be normal priority)
        request = self.queue.get_next_request()
        self.assertEqual(request.request_id, normal_id)
        
        # Complete the request
        self.queue.complete_request(request_id=normal_id, result=None)
        
        # Get the next request (should be low priority)
        request = self.queue.get_next_request()
        self.assertEqual(request.request_id, low_id)
    
    def test_timeout(self):
        """Test request timeout."""
        # Add a request with a timeout
        request_id = self.queue.add_request(
            request_data={"test": "data"},
            priority=RequestPriority.NORMAL,
            timeout_seconds=0.1
        )
        
        # Wait for the timeout
        time.sleep(0.2)
        
        # Check the status
        status = self.queue.get_request_status(request_id)
        self.assertEqual(status["status"], RequestStatus.TIMEOUT.value)


class TestModelResourceManager(unittest.TestCase):
    """Tests for the ModelResourceManager class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.manager = ModelResourceManager(
            max_models=2,
            eviction_strategy=EvictionStrategy.LRU
        )
    
    def test_get_model(self):
        """Test getting a model."""
        # Define a model loader function
        def load_model():
            return {"model": "test"}
        
        # Get the model
        model, error = self.manager.get_model(
            model_id="test_model",
            load_func=load_model
        )
        
        self.assertIsNotNone(model)
        self.assertIsNone(error)
        self.assertEqual(model, {"model": "test"})
    
    def test_eviction(self):
        """Test model eviction."""
        # Define model loader functions
        def load_model_1():
            return {"model": "test1"}
        
        def load_model_2():
            return {"model": "test2"}
        
        def load_model_3():
            return {"model": "test3"}
        
        # Get the first model
        model1, error1 = self.manager.get_model(
            model_id="test_model_1",
            load_func=load_model_1
        )
        
        # Get the second model
        model2, error2 = self.manager.get_model(
            model_id="test_model_2",
            load_func=load_model_2
        )
        
        # Get the third model (should evict the first model)
        model3, error3 = self.manager.get_model(
            model_id="test_model_3",
            load_func=load_model_3
        )
        
        # Try to get the first model again (should be reloaded)
        model1_again, error1_again = self.manager.get_model(
            model_id="test_model_1",
            load_func=load_model_1
        )
        
        self.assertIsNotNone(model1_again)
        self.assertIsNone(error1_again)
        self.assertEqual(model1_again, {"model": "test1"})


class TestInferenceManager(unittest.TestCase):
    """Tests for the InferenceManager class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory for results
        self.temp_dir = tempfile.mkdtemp()
        
        # Define model loader and inference functions
        def model_loader(request_data):
            model_id = f"test_model_{request_data.get('model_id', 'default')}"
            
            def load_func():
                return {"model": model_id}
            
            return model_id, load_func
        
        def model_inference(model, request_data):
            return {"result": f"inference_result_{model['model']}"}
        
        # Create the inference manager
        self.manager = InferenceManager(
            model_loader=model_loader,
            model_inference=model_inference,
            max_workers=2,
            max_models=2,
            result_dir=self.temp_dir,
            cleanup_interval_seconds=0.1
        )
    
    def tearDown(self):
        """Clean up after the test."""
        # Shutdown the inference manager
        self.manager.shutdown(wait=True)
        
        # Remove the temporary directory
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)
    
    def test_submit_request(self):
        """Test submitting a request."""
        # Submit a request
        request_id = self.manager.submit_request(
            request_data={"model_id": "test1"},
            priority=RequestPriority.NORMAL
        )
        
        self.assertIsNotNone(request_id)
        
        # Wait for the request to complete
        for _ in range(10):
            status = self.manager.get_request_status(request_id)
            if status and status.get("status") == "completed":
                break
            time.sleep(0.1)
        
        # Check the status
        status = self.manager.get_request_status(request_id)
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["result"], {"result": "inference_result_test_model_test1"})
    
    def test_cancel_request(self):
        """Test canceling a request."""
        # Submit a request with a delay to ensure it stays in the queue
        with patch.object(self.manager.request_queue, 'get_next_request', return_value=None):
            request_id = self.manager.submit_request(
                request_data={"model_id": "test1"},
                priority=RequestPriority.NORMAL
            )
            
            # Cancel the request
            success = self.manager.cancel_request(request_id)
            
            self.assertTrue(success)
            
            # Check the status
            status = self.manager.get_request_status(request_id)
            self.assertEqual(status["status"], "canceled")


class TestAsyncInferenceConfig(unittest.TestCase):
    """Tests for the AsyncInferenceConfig class."""
    
    def test_default_config(self):
        """Test the default configuration."""
        config = get_default_config()
        
        self.assertEqual(config.max_queue_size, 1000)
        self.assertEqual(config.default_request_priority, "normal")
        self.assertEqual(config.max_workers, 4)
        self.assertEqual(config.max_models, 5)
        self.assertEqual(config.eviction_strategy, "least_recently_used")
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test invalid eviction strategy
        with self.assertRaises(ValueError):
            AsyncInferenceConfig(eviction_strategy="invalid_strategy")
        
        # Test valid configuration
        config = AsyncInferenceConfig(
            max_queue_size=2000,
            max_workers=8,
            max_models=10,
            eviction_strategy="least_frequently_used"
        )
        
        self.assertEqual(config.max_queue_size, 2000)
        self.assertEqual(config.max_workers, 8)
        self.assertEqual(config.max_models, 10)
        self.assertEqual(config.eviction_strategy, "least_frequently_used")


if __name__ == '__main__':
    unittest.main()
