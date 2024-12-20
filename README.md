# Library for onboarding models to OpenAD toolkit
[![License MIT](https://img.shields.io/github/license/acceleratedscience/openad_service_utils)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docs](https://img.shields.io/badge/website-live-brightgreen)](https://acceleratedscience.github.io/openad-docs/) <br>
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)


## Installation

Requirements :<br>
- Linux or Macos <br>
- Python 310.10 or 3.11 <br>

Install the latest version by tag, such as
```shell
pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.3.0
```

## Model Implementations

Look under the examples folder for implementations of models.

- implementation for generation models [readme](examples/generation)
- implementation for properties example [readme](examples/properties)


## Use your own private model not hosted on gt4sd S3 bucket
set the following variables in the os host or python script to your private s3 buckets:

```python
import os
os.environ["GT4SD_S3_HOST"] = "s3.<region>.amazonaws.com"
os.environ["GT4SD_S3_ACCESS_KEY"] = ""
os.environ["GT4SD_S3_SECRET_KEY"] = ""
os.environ["GT4SD_S3_HOST_HUB"] = "s3.<region>.amazonaws.com"
os.environ["GT4SD_S3_ACCESS_KEY_HUB"] = ""
os.environ["GT4SD_S3_SECRET_KEY_HUB"] = ""
```

## Allow Asynchronous results
This feature allows you to define a service as ansynchronously capable. It generates a unique id for the job at random using UUID and will store the result for 3 days before deleting. the user can request the result at any time in the 3 days.

the environment variable 'ASYNC_ALLOW' mut be set for it to work. 

```python
import os
os.environ["ASYNC_ALLOW"] = True 
```
Example:
```
OpenAD:DEFAULT >>  pserve generate with MySimpleGenerator data   for "{'<esol>': -3.2}"  sample 4 async
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

## Experimental Settings
The following are Experimental or Advanced Settings that can be included as Environmental Variables

### AUTO_CLEAR_GPU_MEM
Clears the GPU memory for an Inference call<br>
    Default: `AUTO_CLEAR_GPU_MEM: bool = True`
### AUTO_GARABAGE_COLLECT
Calls the Garbage Collector after an Inference call<br>
    Default `AUTO_GARABAGE_COLLECT: bool = True`
### SERVE_MAX_WORKERS
Enables Multi-Processing of synchronous Calls, Defaults to 1 Thread for safety, depends on performance sizing whether you choose to use more than 1. <br>
    Default: `SERVE_MAX_WORKERS: int = -1`
### ENABLE_CACHE_RESULTS
Enables Caching of Results for command requests, this should only be activated for Deterministic Requests, no functions that use random seeds should this be activated for.<br>
    Default: `ENABLE_CACHE_RESULTS: bool = False`
### ASYNC_POOL_MAX
The Default value for Asynchronous requests is 1, this is so server capacity is managed to the minimum. It is up to the developer and Deployer of a service to set this higher than 1 based on benchmarking. <br>   
    Default `ASYNC_POOL_MAX: int = 1`


## Local Cache locations for models

### Generation Models location

`~/.openad_models / algorithms / algorithm_type / algorithm_name / algorithm_application / algorithm_version`

### Property Models location

`~/.openad_models / properties / domain / algorithm_name / algorithm_application / algorithm_version`
