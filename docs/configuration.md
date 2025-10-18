# Wrapper Configuration Parameters

The model wrapper can be configured using environment variables. The following table lists the available configuration parameters.

| Environment Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `AUTO_CLEAR_GPU_MEM` | boolean | `True` | !important release gpu memory from async workers |
| `AUTO_GARBAGE_COLLECT` | boolean | `True` | Automatically run garbage collection after each request. |
| `ENABLE_CACHE_RESULTS` | boolean | `False` | Enable caching of results. |
| `ASYNC_ALLOW` | boolean | `False` | Enable asynchronous job submission. |
| `ASYNC_CLEANUP_AGE` | integer | `3` | The number of days to keep asynchronous job results before deleting them. |
| `ASYNC_JOB_PATH` | string | `~/.openad_models/openad_async_jobs` | The path to store asynchronous job results. |
| `REDIS_HOST` | string | `localhost` | The hostname of the Redis server. |
| `REDIS_PORT` | integer | `6379` | The port of the Redis server. |
| `REDIS_DB` | integer | `0` | The Redis database to use. |
| `REDIS_PASSWORD` | string | `None` | The password for the Redis server. |
| `REDIS_HIGH_PRIORITY_QUEUE` | string | `high_priority_jobs` | The name of the high priority Redis queue. |
| `REDIS_LOW_PRIORITY_QUEUE` | string | `low_priority_jobs` | The name of the low priority Redis queue. |
| `WORKER_COUNT` | integer | `1` | Number of worker processes to spawn. |
| `JOB_MAX_RETRIES` | integer | `3` | Maximum number of retries for a failed job. |
| `JOB_RETRY_DELAY` | integer | `5` | Seconds to wait before retrying a failed job. |
| `JOB_TTL` | integer | `86400` | Time to live for job keys in Redis (seconds). |
| `REQUEST_CACHE_TTL` | integer | `3600` | Time to live for job request in Redis (seconds). |
| `UPLOAD_STORAGE_DIR` | string | `~/.openad_models/collection_uploads` | Directory to store uploaded files/collections. |
| `UPLOAD_STORAGE_SYNC_INTERVAL` | integer | `60` | Interval in seconds to sync uploaded files. |
| `HOST` | string | `0.0.0.0` | The host to bind the server to. |
| `PORT` | integer | `8080` | The port to bind the server to. |
| `ENABLE_MODEL_CACHING` | boolean | `False` | Enable in-memory caching of models within a worker. Set to False to reduce memory usage at the cost of reloading models for each job. |
| `PROBE_PORT` | integer | `8081` | The port to bind the health probe server to. |
| `UVICORN_LOG_LEVEL` | string | `info` | The log level for uvicorn. |
| `SERVE_MAX_WORKERS` | integer | `1` | number fastapi of worker processes |
| `SERVE_WORKER_GPU_MIN` | integer | `2000` | The minimum GPU memory in MB required for a worker. |

### AWS S3 Configuration

To use your own private model cloud object store, set the following environment variables to your private S3 buckets:

| Environment Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `OPENAD_S3_HOST` | string | `s3.par01.cloud-object-storage.appdomain.cloud` | The hostname of the S3 server. |
| `OPENAD_S3_ACCESS_KEY` | string | `6e9891531d724da89997575a65f4592e` | The access key for the S3 server. |
| `OPENAD_S3_SECRET_KEY` | string | `5997d63c4002cc04e13c03dc0c2db9dae751293dab106ac5` | The secret key for the S3 server. |
| `OPENAD_S3_BUCKET_ALGORITHMS` | string | `gt4sd-cos-algorithms-artifacts` | The S3 bucket for algorithm artifacts. |
| `OPENAD_S3_BUCKET_PROPERTIES` | string | `gt4sd-cos-properties-artifacts` | The S3 bucket for property artifacts. |
| `OPENAD_S3_HOST_HUB` | string | `s3.par01.cloud-object-storage.appdomain.cloud` | The hostname of the S3 server for the hub. |
| `OPENAD_S3_ACCESS_KEY_HUB` | string | `d9536662ebcf462f937efb9f58012830` | The access key for the S3 server for the hub. |
| `OPENAD_S3_SECRET_KEY_HUB` | string | `934d1f3afdaea55ac586f6c2f729ac2ba2694bb8e975ee0b` | The secret key for the S3 server for the hub. |
| `OPENAD_S3_BUCKET_HUB_ALGORITHMS` | string | `gt4sd-cos-hub-algorithms-artifacts` | The S3 bucket for hub algorithm artifacts. |
| `OPENAD_S3_BUCKET_HUB_PROPERTIES` | string | `gt4sd-cos-hub-properties-artifacts` | The S3 bucket for hub property artifacts. |
