# OpenAD Model Wrapper

[OpenAD toolkit]: https://github.com/acceleratedscience/openad-toolkit

_A library to onboard models to the [OpenAD toolkit]_

[![License MIT](https://img.shields.io/github/license/acceleratedscience/openad_service_utils)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docs](https://img.shields.io/badge/website-live-brightgreen)](https://acceleratedscience.github.io/openad-docs/)  
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## Installation

Requirements:

-   Linux or Macos
-   Python 3.10.10+ or 3.11
-   A local Redis server - see [Redis installation](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/)

```shell
pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.4.0
```

<br>

## Why Use the Wrapper?

-   To enable your model(s) to be used in the [OpenAD toolkit]
-   To wrap your model(s) in a quick and easy FastAPI service  
    &rarr; No need to write all the FastAPI endpoints from scratch
-   To containerize your model(s) in Kubernetes (e.g. OpenShift), Docker, Podman, etc.

The OpenAD Model Wrapper makes your container code simpler, following the format of other models available in the [OpenAD model service](https://openad.accelerate.science/docs/model-service/available-models).

<br>

## Advanced

### Use your own private model not hosted on public OpenAD S3 bucket

To use your own private model cloud object store, set the following variables in the os host or python script to your private s3 buckets:

```python
import os
os.environ["OPENAD_S3_HOST"] = "s3.<region>.amazonaws.com"
os.environ["OPENAD_S3_ACCESS_KEY"] = ""
os.environ["OPENAD_S3_SECRET_KEY"] = ""
os.environ["OPENAD_S3_HOST_HUB"] = "s3.<region>.amazonaws.com"
os.environ["OPENAD_S3_ACCESS_KEY_HUB"] = ""
os.environ["OPENAD_S3_SECRET_KEY_HUB"] = ""
```

### Allow Asynchronous results

Set `ASYNC_ALLOW` to `True` to configure your inference service as ansynchronous.
With this enabled, each inference job is assigned a unique, random id using
UUID. The system stores the result for 3 days before it is deleted. The
inference user can request the result using the job id at any time in the 3 days.

```python
import os
os.environ["ASYNC_ALLOW"] = True
```

Example:

```text
OpenAD:DEFAULT >>  pserve generate with MySimpleGenerator data for "{'<esol>': -3.2}"  sample 4 async
✔ Request Returned
{'id': '8c2cfb68-b037-11ef-9223-acde48001122'}
OpenAD:DEFAULT >>  get model service 'pserve' result '8c2cfb68-b037-11ef-9223-acde48001122'
job is still running
OpenAD:DEFAULT >>  get model service 'pserve' result '8c2cfb68-b037-11ef-9223-acde48001122'

  pred1    pred2
-------  -------
      1        2

Next up, you can run: result open/edit/copy/display/as dataframe/save [as '<filename.csv>']

```

<br>

## Experimental Settings

The following are experimental or advanced settings that can be included as environmental variables

<!-- prettier-ignore -->
**AUTO_CLEAR_GPU_MEM**  
Clears the GPU memory for an Inference call

<pre>Type:    `bool`</pre>
<pre>Default: `True`</pre>

**AUTO_GARABAGE_COLLECT**  
Calls the Garbage Collector after an Inference call  
Default `AUTO_GARABAGE_COLLECT: bool = True`

**SERVE_MAX_WORKERS**  
Enables multi-processing of synchronous calls.  
Defaults to one thread for safety, depends on performance sizing whether you choose to use more.  
Default: `SERVE_MAX_WORKERS: int = -1`

**ENABLE_CACHE_RESULTS**  
Enables caching of results for command requests.  
This should only be activated for deterministic requests, no functions that use random seeds should this be activated for.  
Default: `ENABLE_CACHE_RESULTS: bool = False`

<br>

## Job_Manager Settings

### Examples for each Variable:

1. **QUEUES**: If you want to set the number of subprocesses to 4 (default is 2), you would add the following line in your environment setup (e.g., `.env` file or system environment variables):

    ```
    JOB_QUEUES=4
    ```

2. **ASYNC_PATH**: If you want to save async job results in a custom directory, e.g., the default is `/tmp/openad_async_archive`, update the environment variable like so:

    ```
    ASYNC_PATH=~/openad_async_archive
    ```

    This will make `ASYNC_PATH` equal to `~/openad_async_archive`.

3. **ASYNC_CLEANUP_AGE**: Sets the Clean up age for asynchronous job results on disk, default is 3 days, you can update the environment variable:

    ```
    ASYNC_CLEANUP_AGE=7
    ```

    This will make `ASYNC_CLEANUP_AGE` equal to `7` days.

4. **ASYNC_QUEUE_ALLOCATION**: If you want to allocate 2 subprocesses for handling async requests, set the environment variable as follows:

    ```
    ASYNC_QUEUE_ALLOCATION=2
    ```

    This will make `ASYNC_QUEUE_ALLOCATION` equal to `2`.

5. **ASYNC_ALLOW**: To enable asynchronous requests, update the environment variable, the default value for this is `False`:

    ```
    ASYNC_ALLOW=True
    ```

    This will make `ASYNC_ALLOW` equal to `True`, enabling async requests. Conversely, to disable them, set it to `False`:

## Local Cache locations for models

### Generation Models location

`~/.openad_models / algorithms / algorithm_type / algorithm_name / algorithm_application / algorithm_version`

### Property Models location

`~/.openad_models / properties / domain / algorithm_name / algorithm_application / algorithm_version`
