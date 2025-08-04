# OpenAD Model Wrapper

_A library to onboard models to the [OpenAD toolkit]_

[![License MIT](https://img.shields.io/github/license/acceleratedscience/openad_service_utils)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docs](https://img.shields.io/badge/website-live-brightgreen)](https://acceleratedscience.github.io/openad-docs/)  
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

<br>

## About

The OpenAD Model Wrapper lets you wrap any model into a standardized RESTful API so it can be used in the [OpenAD Toolkit].

-   Enable your model(s) to be used by the [OpenAD model service]
-   Wrap your model(s) in a quick and easy [FastAPI](https://fastapi.tiangolo.com/) service  
    &rarr; No need to write all the FastAPI endpoints from scratch
-   Containerize your model(s) in Kubernetes (e.g. OpenShift) for Docker, Podman, etc.
    &rarr; Simpler container code, following the format of other models available in the [OpenAD model service].

<br>

## Tl;dr

1. Download this repo

    ```
    git clone git@github.com:acceleratedscience/openad_service_utils.git
    ```

    <!--
    pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.4.0
    -->

2. Choose the appropriate wrapper:

    - For generation models
        1. [Classic implentation](src/openad_service_utils/implementation/generation/classic.py) (use when xxx)
        2. [Simple implementation](src/openad_service_utils/implementation/generation/simple.py) (use when xxx)
    - Property prediction models
        1. [Simple implementation](src/openad_service_utils/implementation/properties/simple.py)

3. Separate your model code into **imports** / **instantiation** / **execution** and insert each code into the appropriate tags:

    ```

    ```

## Installation

Requirements:

-   Linux or Macos
-   Python 3.10.10+ or 3.11
-   A local Redis server - see [Redis installation](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/)

```shell
pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.4.0
```

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

Set `ASYNC_ALLOW` to `True` to configure your inference service as asynchronous.
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

## Job_Manager Settings

The following are settings related to the job manager that can be included as environmental variables.

| Parameter Name         | Type | Default                     | Description                                                               |
| :--------------------- | :--- | :-------------------------- | :------------------------------------------------------------------------ |
| JOB_QUEUES             | int  | 2                           | The number of subprocesses that is allowed                                |
| ASYNC_ALLOW            | bool | True                        | Enable asynchronous requests                                              |
| ASYNC_QUEUE_ALLOCATION | int  | 1                           | The number of subprocesses that is allowed for async requests             |
| ASYNC_PATH             | str  | `/tmp/openad_async_archive` | Save async job results in a custom directory                              |
| ASYNC_CLEANUP_AGE      | int  | 3                           | Number of days after which asynchronous job results are cleaned from disk |

<br>

## Experimental Settings

The following are experimental or advanced settings that can be included as environmental variables.

| Parameter Name          | Type | Default | Description                                                                                                                                          |
| :---------------------- | :--- | :------ | :--------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AUTO_CLEAR_GPU_MEM`    | bool | True    | Clears the GPU memory for an Inference call                                                                                                          |
| `AUTO_GARABAGE_COLLECT` | bool | True    | Calls the Garbage Collector after an Inference call                                                                                                  |
| `SERVE_MAX_WORKERS`     | int  | -1      | Enables multi-processing of synchronous calls. Defaults to one thread for safety, choose more depending on performance sizing                        |
| `ENABLE_CACHE_RESULTS`  | bool | False   | Enables caching of results for command requests. This should only be activated for deterministic requests, never for functions that use random seeds |

<br>

## Cache Files

The cache files for your models are stored on the following locations:

-   Generation models

    ```
    ~/.openad_models/algorithms/<algorithm_type>/<algorithm_name>/<algorithm_application>/<algorithm_version>
    ```

-   Property models

    ```
    ~/.openad_models/properties/<domain>/<algorithm_name>/<algorithm_application>/<algorithm_version>
    ```

<!-- Links -->

[OpenAD toolkit]: https://github.com/acceleratedscience/openad-toolkit
[OpenAD model service]: https://openad.accelerate.science/docs/model-service/available-models
