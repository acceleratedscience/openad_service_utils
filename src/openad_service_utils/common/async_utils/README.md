# Asynchronous Inference System for OpenAD

This module provides a scalable, robust asynchronous request handling system for model inference in OpenAD. It is designed to process multiple concurrent model inference requests without blocking, manage request priorities, handle timeouts, and optimize resource usage.

## Architecture

The asynchronous inference system consists of several key components:

### 1. Request Queue

The `RequestQueue` class manages incoming requests with the following features:
- Priority-based scheduling (LOW, NORMAL, HIGH, CRITICAL)
- Request timeout handling
- Status tracking for in-progress requests
- Concurrency control

### 2. Resource Manager

The `ModelResourceManager` class handles model loading and memory management:
- Controls the maximum number of simultaneously loaded models
- Optimizes memory usage during peak loads
- Implements model eviction strategies (LRU, LFU, SIZE)
- Tracks model usage statistics

### 3. Inference Manager

The `InferenceManager` class ties together the request queue and resource manager:
- Accepts and queues inference requests
- Manages model loading and unloading
- Processes requests in priority order
- Provides status updates for in-progress requests
- Handles timeouts and errors
- Implements model caching

### 4. Service Adapters

The `PropertyServiceAdapter` and `GenerationServiceAdapter` classes integrate the asynchronous inference system with the existing OpenAD services:
- Bridge between the existing API and the new asynchronous system
- Provide a clean interface for submitting requests and retrieving results

### 5. Configuration

The `AsyncInferenceConfig` class provides configuration options for the asynchronous inference system:
- Request queue settings
- Worker settings
- Model resource management settings
- Result storage settings
- Model-specific settings

## API Usage

### Submitting Asynchronous Requests

To submit an asynchronous request, add the following parameters to your existing request:

```json
{
  "service_type": "get_molecule_property",
  "service_name": "your_service",
  "parameters": {
    "property_type": ["your_property"],
    "subjects": ["your_subject"]
  },
  "async": true,
  "use_enhanced_async": true,
  "priority": "normal",
  "timeout_seconds": 300
}
```

Parameters:
- `async`: Set to `true` to enable asynchronous processing
- `use_enhanced_async`: Set to `true` to use the new enhanced asynchronous system
- `priority`: Optional priority level ("low", "normal", "high", "critical")
- `timeout_seconds`: Optional timeout in seconds

The response will include a request ID:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Checking Request Status

To check the status of an asynchronous request, use one of the following methods:

#### Method 1: Using the service endpoint

```json
{
  "service_type": "get_result",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Method 2: Using the dedicated status endpoint

```
GET /async/status/550e8400-e29b-41d4-a716-446655440000
```

The response will include the request status:

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2025-03-07T15:30:00.000Z",
  "started_at": "2025-03-07T15:30:01.000Z",
  "completed_at": "2025-03-07T15:30:10.000Z",
  "elapsed_time": "10.00s",
  "processing_time": "9.00s",
  "result": [
    {
      "subject": "your_subject",
      "property": "your_property",
      "result": "your_result"
    }
  ]
}
```

Possible status values:
- `pending`: The request is waiting in the queue
- `processing`: The request is being processed
- `completed`: The request has completed successfully
- `failed`: The request has failed
- `timeout`: The request has timed out
- `canceled`: The request has been canceled

### Canceling Requests

To cancel a pending request, use the following endpoint:

```
DELETE /async/status/550e8400-e29b-41d4-a716-446655440000
```

The response will indicate whether the cancellation was successful:

```json
{
  "result": "Request canceled successfully"
}
```

### Getting System Statistics

To get statistics about the asynchronous inference system, use the following endpoint:

```
GET /async/stats
```

The response will include statistics about the request queue and model cache:

```json
{
  "property_service": {
    "queue": {
      "queue_length": 5,
      "processing_count": 2,
      "total_requests": 10,
      "status_counts": {
        "pending": 5,
        "processing": 2,
        "completed": 2,
        "failed": 1,
        "timeout": 0,
        "canceled": 0
      },
      "priority_counts": {
        "LOW": 1,
        "NORMAL": 3,
        "HIGH": 1,
        "CRITICAL": 0
      },
      "max_concurrent_requests": 4
    },
    "models": {
      "loaded_models": 3,
      "loading_models": 1,
      "total_memory_mb": 1500,
      "max_models": 5,
      "max_memory_mb": 4000,
      "eviction_strategy": "least_recently_used",
      "models": {
        "model_1": {
          "size_mb": 500,
          "load_time": "2025-03-07T15:00:00.000Z",
          "last_used": "2025-03-07T15:30:00.000Z",
          "use_count": 5,
          "is_loading": false
        },
        "model_2": {
          "size_mb": 700,
          "load_time": "2025-03-07T15:10:00.000Z",
          "last_used": "2025-03-07T15:20:00.000Z",
          "use_count": 3,
          "is_loading": false
        },
        "model_3": {
          "size_mb": 300,
          "load_time": "2025-03-07T15:20:00.000Z",
          "last_used": "2025-03-07T15:25:00.000Z",
          "use_count": 2,
          "is_loading": false
        },
        "model_4": {
          "size_mb": 800,
          "load_time": "2025-03-07T15:25:00.000Z",
          "last_used": "2025-03-07T15:25:00.000Z",
          "use_count": 0,
          "is_loading": true
        }
      }
    },
    "workers": 4
  },
  "generation_service": {
    // Similar structure to property_service
  },
  "config": {
    // Configuration settings
  }
}
```

## Configuration Options

The asynchronous inference system can be configured using environment variables with the prefix `OPENAD_ASYNC_`. For example:

```bash
# Request queue settings
export OPENAD_ASYNC_MAX_QUEUE_SIZE=1000
export OPENAD_ASYNC_DEFAULT_REQUEST_TIMEOUT=300
export OPENAD_ASYNC_DEFAULT_REQUEST_PRIORITY=normal

# Worker settings
export OPENAD_ASYNC_MAX_WORKERS=4

# Model resource management settings
export OPENAD_ASYNC_MAX_MODELS=5
export OPENAD_ASYNC_MAX_MEMORY_MB=4000
export OPENAD_ASYNC_EVICTION_STRATEGY=least_recently_used
export OPENAD_ASYNC_MEMORY_HEADROOM_MB=1000

# Result storage settings
export OPENAD_ASYNC_RESULT_TTL_HOURS=24
export OPENAD_ASYNC_RESULT_DIR=/tmp/openad_async_results
export OPENAD_ASYNC_CLEANUP_INTERVAL_SECONDS=3600
```

### Configuration Options Reference

#### Request Queue Settings

- `MAX_QUEUE_SIZE`: Maximum number of requests in the queue (default: 1000)
- `DEFAULT_REQUEST_TIMEOUT`: Default timeout for requests in seconds (default: None)
- `DEFAULT_REQUEST_PRIORITY`: Default priority for requests (default: "normal")

#### Worker Settings

- `MAX_WORKERS`: Maximum number of worker threads for processing requests (default: 4)

#### Model Resource Management Settings

- `MAX_MODELS`: Maximum number of models to keep loaded simultaneously (default: 5)
- `MAX_MEMORY_MB`: Maximum memory usage in MB (default: None)
- `EVICTION_STRATEGY`: Strategy to use when evicting models (default: "least_recently_used")
- `MEMORY_HEADROOM_MB`: Amount of memory to keep free in MB (default: 1000)

#### Result Storage Settings

- `RESULT_TTL_HOURS`: Time to live for results in hours (default: 24)
- `RESULT_DIR`: Directory to store results (default: "/tmp/openad_async_results")
- `CLEANUP_INTERVAL_SECONDS`: Interval for cleaning up old results in seconds (default: 3600)

## Error Handling

The asynchronous inference system provides comprehensive error handling for various scenarios:

### Failed Model Loads

If a model fails to load, the request will be marked as failed with an appropriate error message.

### Timeouts

Requests can time out in two ways:
1. While waiting in the queue (if the queue timeout is exceeded)
2. During processing (if the processing timeout is exceeded)

In both cases, the request will be marked as timed out with an appropriate error message.

### Resource Exhaustion

If the system runs out of resources (e.g., memory), it will attempt to free up resources by evicting models according to the configured eviction strategy. If this fails, the request will be marked as failed with an appropriate error message.

### Network/Connection Issues

If there are network or connection issues during model loading or inference, the request will be marked as failed with an appropriate error message.

## Horizontal Scaling

The asynchronous inference system is designed to be horizontally scalable. Multiple instances of the OpenAD service can be deployed behind a load balancer, with each instance running its own asynchronous inference system.

To enable horizontal scaling:

1. Deploy multiple instances of the OpenAD service
2. Configure a load balancer to distribute requests across the instances
3. Use a shared storage solution for result files (e.g., NFS, S3)
4. Configure the `RESULT_DIR` setting to point to the shared storage

## Monitoring and Logging

The asynchronous inference system provides comprehensive logging and monitoring capabilities:

### Logging

All significant events are logged with appropriate log levels:
- INFO: Normal operation events (request submission, completion, etc.)
- WARNING: Potential issues (timeouts, resource constraints, etc.)
- ERROR: Errors that prevent request processing

### Monitoring

The `/async/stats` endpoint provides detailed statistics about the asynchronous inference system, including:
- Queue statistics (length, processing count, status counts, etc.)
- Model statistics (loaded models, memory usage, etc.)
- Worker statistics (number of workers)

These statistics can be used to monitor the health and performance of the system.

## Backward Compatibility

The asynchronous inference system is designed to be backward compatible with the existing OpenAD API. Existing synchronous requests will continue to work as before, and the legacy asynchronous system is still supported.

To use the new asynchronous system, add the `use_enhanced_async` parameter to your request:

```json
{
  "async": true,
  "use_enhanced_async": true
}
```

If `use_enhanced_async` is not specified or is set to `false`, the legacy asynchronous system will be used.
