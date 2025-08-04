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
  "service_type": "molecule",
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

To retrieve the results of an asynchronous job, send a request with the `service_type` set to `get_result` and the `url` field set to the job ID.

**Example:**

```json
{
  "service_type": "get_result",
  "url": "f1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

The server will respond with the results of the job, or a status indicating that the job is still pending.
