# Wrapper Configuration Parameters

The model wrapper can be configured using environment variables. The following table lists the available configuration parameters.

| Environment Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `AUTO_CLEAR_GPU_MEM` | boolean | `True` | Automatically clear GPU memory after each request. |
| `AUTO_GARABAGE_COLLECT` | boolean | `True` | Automatically run garbage collection after each request. |
| `SERVE_MAX_WORKERS` | integer | `-1` | The maximum number of worker processes to use. If set to -1, the number of workers will be determined automatically based on the available resources. |
| `ENABLE_CACHE_RESULTS` | boolean | `False` | Enable caching of results. |
| `ASYNC_POOL_MAX` | integer | `1` | The maximum number of processes to use for asynchronous jobs. |
| `ASYNC_ALLOW` | boolean | `False` | Enable asynchronous job submission. |
| `ASYNC_CLEANUP_AGE` | integer | `3` | The number of days to keep asynchronous job results before deleting them. |
| `ASYNC_QUEUE_ALLOCATION` | integer | `1` | The number of queues to use for asynchronous jobs. |
| `ASYNC_JOB_PATH` | string | `/tmp/openad_async_archive` | The path to store asynchronous job results. |
| `REDIS_JOB_QUEUES` | integer | `1` | The number of Redis queues to use for jobs. |
| `REDIS_HOST` | string | `localhost` | The hostname of the Redis server. |
| `REDIS_PORT` | integer | `6379` | The port of the Redis server. |
| `REDIS_DB` | integer | `0` | The Redis database to use. |
| `REDIS_PASSWORD` | string | `None` | The password for the Redis server. |

### AWS S3 Configuration

To use your own private model cloud object store, set the following environment variables to your private S3 buckets:

| Environment Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `OPENAD_S3_HOST` | string | `None` | The hostname of the S3 server. |
| `OPENAD_S3_ACCESS_KEY` | string | `None` | The access key for the S3 server. |
| `OPENAD_S3_SECRET_KEY` | string | `None` | The secret key for the S3 server. |
| `OPENAD_S3_HOST_HUB` | string | `None` | The hostname of the S3 server for the hub. |
| `OPENAD_S3_ACCESS_KEY_HUB` | string | `None` | The access key for the S3 server for the hub. |
| `OPENAD_S3_SECRET_KEY_HUB` | string | `None` | The secret key for the S3 server for the hub. |
