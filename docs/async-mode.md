# Asynchronous Mode Configuration

This guide provides a step-by-step setup for using the asynchronous endpoints of the model wrapper.

## 1. Enable Asynchronous Mode

To enable asynchronous mode, set the `ASYNC_ALLOW` environment variable to `True`.

```bash
export ASYNC_ALLOW=True
```

## 2. Configure Redis

The model wrapper uses Redis for managing asynchronous jobs. Make sure you have a Redis server running and configure the following environment variables to connect to it:

*   `REDIS_HOST`: The hostname of the Redis server (default: `localhost`).
*   `REDIS_PORT`: The port of the Redis server (default: `6379`).
*   `REDIS_DB`: The Redis database to use (default: `0`).
*   `REDIS_PASSWORD`: The password for the Redis server (default: `None`).

## 3. Submit an Asynchronous Job

To submit an asynchronous job, add the `async` field to your request and set it to `True`.

**Example:**

```json
{
  "service_type": "get_molecule_property",
  "service_name": "MySimplePredictor",
  "parameters": {
    "property_type": ["LogP", "TPSA"],
    "subjects": ["CCO", "CCC"]
  },
  "async": true
}
```

The server will respond with a job ID that you can use to retrieve the results later.

```json
{
  "job_id": "f1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

## 4. Retrieve the Results

To retrieve the results of an asynchronous job, send a request with the `service_type` set to `get_result` and the `url` field set to the job ID. The server will respond with the status of the job.

### JSON-Based Results

If the predictor returns a JSON-serializable result, the response will be the result itself once the job is complete.

**Example:**
```json
{
  "service_type": "get_result",
  "url": "f1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

### File-Based Results

If the predictor returns a `FileResponse` object, the response will contain a `download_url` once the job is complete.

**Example:**
```json
{
    "status": "completed",
    "result_type": "file",
    "download_url": "/service/download/f1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

## 5. Asynchronous File Download Workflow Example

This example demonstrates the full lifecycle of an asynchronous, file-based prediction using `curl` and `jq`.

### Step 1: Upload the Input File

First, upload your input file (e.g., `my_mesh.vtk`) to the `/service/upload` endpoint.

```bash
FILE_KEY=$(curl -X POST "http://localhost:8080/service/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@my_mesh.vtk" | jq -r .file_key)

echo "File key: $FILE_KEY"
```

### Step 2: Submit the Asynchronous Job

Next, submit the prediction job to the `/service` endpoint with `"async": true`, using the `file_key` obtained in the previous step.

```bash
JOB_ID=$(curl -X POST "http://localhost:8080/service" \
  -H "Content-Type: application/json" \
  -d '{
    "service_type": "get_mesh_property",
    "service_name": "surface_property_prediction",
    "parameters": {
      "property_type": ["SurfaceArea"]
    },
    "file_keys": ["'$FILE_KEY'"],
    "async": true
  }' | jq -r .job_id)

echo "Job ID: $JOB_ID"
```

### Step 3: Poll for Job Completion

Poll the `get_result` endpoint until the status is "completed".

```bash
DOWNLOAD_URL=""
while [ -z "$DOWNLOAD_URL" ]; do
  echo "Checking job status..."
  RESPONSE=$(curl -s -X POST "http://localhost:8080/service" \
    -H "Content-Type: application/json" \
    -d '{"service_type": "get_result", "url": "'$JOB_ID'"}')
  
  STATUS=$(echo $RESPONSE | jq -r .status)
  
  if [ "$STATUS" == "completed" ]; then
    DOWNLOAD_URL=$(echo $RESPONSE | jq -r .download_url)
    echo "Job complete. Download URL: $DOWNLOAD_URL"
  else
    echo "Job is still pending. Waiting 5 seconds..."
    sleep 5
  fi
done
```

### Step 4: Download the Result File

Finally, use the `download_url` to download the result file.

```bash
curl -o "prediction_result.json" "http://localhost:8080$DOWNLOAD_URL"

echo "Result downloaded to prediction_result.json"
```
