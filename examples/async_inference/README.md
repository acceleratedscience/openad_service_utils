# OpenAD Asynchronous Inference Examples

This directory contains examples demonstrating how to use the enhanced asynchronous inference system in OpenAD.

## Configuration Example

The `async_config_example.json` file demonstrates how to configure the asynchronous inference system. You can use this file as a template for your own configuration.

To use a configuration file, set the `OPENAD_ASYNC_CONFIG_FILE` environment variable to the path of your configuration file:

```bash
export OPENAD_ASYNC_CONFIG_FILE=/path/to/your/config.json
```

Alternatively, you can use environment variables to configure the system. See the [Configuration Options](../../src/openad_service_utils/common/async_utils/README.md#configuration-options) section in the main README for more information.

## Load Testing

The `load_test.py` script demonstrates how to perform load testing on the asynchronous inference system. It submits multiple requests in parallel and monitors their progress, providing statistics on the system's performance.

### Usage

```bash
# Run a load test with 100 requests and 10 concurrent requests
python load_test.py --url http://localhost:8080 \
    --num-requests 100 \
    --concurrency 10 \
    --service-type get_molecule_property \
    --service-name molecule_property \
    --property-types logp,tpsa \
    --subjects-file molecules.txt \
    --priorities low,normal,high \
    --max-wait-time 600 \
    --output results.json

# Run a simple load test with default parameters
python load_test.py
```

### Command-line Arguments

- `--url`: Base URL of the OpenAD API (default: http://localhost:8080)
- `--num-requests`: Number of requests to submit (default: 10)
- `--concurrency`: Maximum number of concurrent requests (default: 5)
- `--service-type`: Type of service (default: get_molecule_property)
- `--service-name`: Name of the service (default: molecule_property)
- `--property-types`: Comma-separated list of property types (default: logp)
- `--subjects-file`: File containing SMILES strings (one per line)
- `--subject`: Default subject if no file is provided (default: CC(=O)OC1=CC=CC=C1C(=O)O)
- `--priorities`: Comma-separated list of priorities (default: normal)
- `--timeout`: Request timeout in seconds (default: None)
- `--poll-interval`: Interval between status checks in seconds (default: 1.0)
- `--max-wait-time`: Maximum time to wait for completion in seconds (default: 300.0)
- `--output`: Output file for results (JSON)

### Example Output

```
Running load test with 10 requests, 5 concurrency
Service: get_molecule_property/molecule_property
Property types: ['logp']
Number of subjects: 1
Priorities: ['normal']
Submitted request 550e8400-e29b-41d4-a716-446655440000
Submitted request 550e8400-e29b-41d4-a716-446655440001
...
Request 550e8400-e29b-41d4-a716-446655440000 completed in 5.23s
Request 550e8400-e29b-41d4-a716-446655440001 completed in 6.45s
...

Load Test Results:
{'avg_completion_time': 5.84,
 'completed_requests': 10,
 'error_requests': 0,
 'failed_requests': 0,
 'max_completion_time': 7.12,
 'min_completion_time': 5.23,
 'requests_per_second': 1.71,
 'timeout_requests': 0,
 'total_requests': 10,
 'total_time': 5.84}

Detailed results saved to results.json
```

## Prerequisites

- Python 3.7 or higher
- `requests` library (`pip install requests`)
- Running OpenAD service with asynchronous inference enabled

## Example Client

The `async_client_example.py` script demonstrates how to:

1. Submit asynchronous requests to the OpenAD API
2. Check the status of asynchronous requests
3. Wait for request completion
4. Retrieve results
5. Cancel pending requests
6. Get system statistics

### Usage

```bash
# Submit a request and wait for completion
python async_client_example.py --url http://localhost:8080 \
    --service-type get_molecule_property \
    --service-name molecule_property \
    --property-type logp \
    --subject "CC(=O)OC1=CC=CC=C1C(=O)O" \
    --priority normal \
    --timeout 300 \
    --max-wait-time 60

# Get system statistics
python async_client_example.py --url http://localhost:8080 --stats

# Cancel a request
python async_client_example.py --url http://localhost:8080 --cancel REQUEST_ID
```

### Command-line Arguments

- `--url`: Base URL of the OpenAD API (default: http://localhost:8080)
- `--service-type`: Type of service (default: get_molecule_property)
- `--service-name`: Name of the service (default: molecule_property)
- `--property-type`: Property type (default: logp)
- `--subject`: Subject (e.g., SMILES string) (default: CC(=O)OC1=CC=CC=C1C(=O)O)
- `--priority`: Request priority (low, normal, high, critical) (default: normal)
- `--timeout`: Request timeout in seconds (default: None)
- `--poll-interval`: Interval between status checks in seconds (default: 1.0)
- `--max-wait-time`: Maximum time to wait for completion in seconds (default: 60.0)
- `--stats`: Get system statistics
- `--cancel`: Cancel a request with the specified ID

## API Usage Examples

### Submitting an Asynchronous Request

```python
import requests

# Prepare the request data
request_data = {
    "service_type": "get_molecule_property",
    "service_name": "molecule_property",
    "parameters": {
        "property_type": ["logp"],
        "subjects": ["CC(=O)OC1=CC=CC=C1C(=O)O"],
        "subject_type": "smiles"
    },
    "async": True,
    "use_enhanced_async": True,
    "priority": "normal",
    "timeout_seconds": 300
}

# Submit the request
response = requests.post("http://localhost:8080/service", json=request_data)
response.raise_for_status()

# Get the request ID
result = response.json()
request_id = result["request_id"]
print(f"Request ID: {request_id}")
```

### Checking Request Status

```python
import requests

# Get the request status
response = requests.get(f"http://localhost:8080/async/status/{request_id}")
response.raise_for_status()

# Print the status
status = response.json()
print(f"Status: {status['status']}")
```

### Waiting for Request Completion

```python
import requests
import time

# Wait for completion
while True:
    response = requests.get(f"http://localhost:8080/async/status/{request_id}")
    response.raise_for_status()
    
    status = response.json()
    print(f"Status: {status['status']}")
    
    if status["status"] in ("completed", "failed", "timeout", "canceled"):
        break
    
    time.sleep(1.0)

# Print the result
if status["status"] == "completed":
    print("Result:", status["result"])
else:
    print(f"Error: {status.get('error', 'Unknown error')}")
```

### Canceling a Request

```python
import requests

# Cancel the request
response = requests.delete(f"http://localhost:8080/async/status/{request_id}")
response.raise_for_status()

# Print the result
result = response.json()
print(f"Cancellation result: {result}")
```

### Getting System Statistics

```python
import requests

# Get system statistics
response = requests.get("http://localhost:8080/async/stats")
response.raise_for_status()

# Print the statistics
stats = response.json()
print("System statistics:", stats)
```

## Additional Resources

For more information about the asynchronous inference system, see the [README.md](../../src/openad_service_utils/common/async_utils/README.md) file in the `src/openad_service_utils/common/async_utils` directory.
