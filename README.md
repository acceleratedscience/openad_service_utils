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

The OpenAD Model Wrapper lets you wrap any model into a standardized RESTful API so it can be used in the [OpenAD Toolkit]. This library provides the utilities to create and run OpenAD services, including:

-   Wrapping your model(s) in a quick and easy [FastAPI](https://fastapi.tiangolo.com/) service.
-   Containerizing your model(s) for use in Kubernetes, Docker, Podman, etc.

<br>

## Getting Started

### 1. Installation

Requirements:

-   Linux or Macos
-   Python 3.10.10+ or 3.11
-   A local Redis server - see [Redis installation](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/)

```shell
pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.4.0
```

### 2. Wrapping Your Model

To wrap your model, you can use one of the provided templates. See the [Sample Configuration Templates](./docs/templates.md) for examples of how to wrap different types of models.

For a step-by-step guide, see the [Foundational Tutorial](./tutorials/tutorial-basis.md).

### 3. Running the Service

Once you have wrapped your model, you can start the service by running your Python script.

### 4. Using with Openad Toolkit

The [Openad Toolkit](https://github.com/acceleratedscience/openad-toolkit) allows us to run inference through a TUI. See detailed docs [here](https://openad.accelerate.science/docs/model-service/using-models/)

Install the toolkit and run your model inference.

```shell
pip install openad
openad
```

Now connect your model and run an inference.
```shell
>>> catalog model service from remote 'http://localhost:8080' as 'my_model'

>>> my_model ? # see detailed information about your model

>>> my_model <COMMAND> # run an inference based off your model configuration
```

<br>

## Documentation

For more detailed documentation, please see the [docs](./docs) directory. The documentation includes information on:

-   [Architecture Overview](./docs/architecture.md)
-   [Input/Output Schema Examples](./docs/input-output.md)
-   [Model Selection & Switching Logic](./docs/model-selection.md)
-   [Wrapper Configuration Parameters](./docs/configuration.md)
-   [Async Mode Configuration](./docs/async-mode.md)
-   [Troubleshooting Guide](./docs/troubleshooting.md)

<!-- Links -->

[OpenAD toolkit]: https://github.com/acceleratedscience/openad-toolkit
[OpenAD model service]: https://openad.accelerate.science/docs/model-service/available-models
