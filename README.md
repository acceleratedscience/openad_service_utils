# OpenAD Model Wrapper

_A library to onboard models to the [OpenAD toolkit]_

[![License MIT](https://img.shields.io/github/license/acceleratedscience/openad_service_utils)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Docs](https://img.shields.io/badge/website-live-brightgreen)](https://acceleratedscience.github.io/openad-docs/)  
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)

## About

The OpenAD Model Wrapper is a Python library that simplifies the process of deploying machine learning models as production-ready services. It is specifically designed for scientific use cases, such as **molecular property prediction** (e.g., solubility, toxicity) and **de novo molecular generation**.

By wrapping your model with this library, you can:

-   **Standardize Your Model's API:** Expose your model through a standardized API, making it easy to integrate with other tools and workflows.
-   **Seamlessly Integrate with the OpenAD Toolkit:**  The wrapper is designed to work out-of-the-box with the [OpenAD Toolkit], a powerful platform for accelerated discovery.
-   **Simplify Deployment:** The library provides a straightforward path to containerizing your model with Docker and deploying it to scalable platforms like Kubernetes.

<br>

## Getting Started

### 1. Installation

Requirements:

-   Linux or Macos
-   Python 3.10.10+ or 3.11
-   A local Redis server - see [Redis installation](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/)

```shell
pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.5.0
```

### 2. Wrapping Your Model

To wrap your model, you can use one of the provided templates. See the [Sample Configuration Templates](./docs/templates.md) for examples of how to wrap different types of models.

For a step-by-step guide, see the [Foundational Tutorial](./tutorials/tutorial-basis.md).

### 3. Running the Service

Once you have wrapped your model, you can start the service by running your Python script. I will be served by default on http://localhost:8080

### 4. Using with Openad Toolkit

The [Openad Toolkit](https://github.com/acceleratedscience/openad-toolkit) allows us to run inference through a TUI. See detailed docs [here](https://openad.accelerate.science/docs/model-service/using-models/)

Install the toolkit.

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
-   [Sample Configuration Templates](./docs/templates.md)
-   [Wrapper Configuration Parameters](./docs/configuration.md)
-   [Model Selection & Switching Logic](./docs/model-selection.md)
-   [Async Mode Configuration](./docs/async-mode.md)
-   [API Reference](./docs/api-reference.md)
-   [Input/Output Schema Examples](./docs/input-output.md)
-   [Deployment Guide](./docs/deployment.md)
-   [Troubleshooting Guide](./docs/troubleshooting.md)

<!-- Links -->

[OpenAD toolkit]: https://github.com/acceleratedscience/openad-toolkit
[OpenAD model service]: https://openad.accelerate.science/docs/model-service/available-models
