# Wrapper Configuration Parameters

The model wrapper can be configured using environment variables. The following table lists the available configuration parameters.

| Environment Variable | Type | Default | Description |
| --- | --- | --- | --- |
| `AUTO_CLEAR_GPU_MEM` | boolean | `True` | Automatically clear GPU memory after each request. |
| `AUTO_GARBAGE_COLLECT` | boolean | `True` | Automatically run garbage collection after each request. |
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
