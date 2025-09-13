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
pip install git+https://github.com/acceleratedscience/openad_service_utils.git@0.5.2
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

This project is documented in the `docs/` directory. Below is an overview of the available documents.

-   **Core Concepts**
    -   [`architecture.md`](./docs/architecture.md): Provides a high-level overview of the service's components and request lifecycle, including an explanation of the different [Execution Workflows](./docs/architecture.md#execution-workflows).
    -   [`model-selection.md`](./docs/model-selection.md): Explains how the service uses a combination of `service_type` and `service_name` to route requests to the correct model.
-   **Implementation Guides**
    -   [`templates.md`](./docs/templates.md): Contains sample code and templates for wrapping different types of models, including those that handle file-based I/O.
    -   [`async-mode.md`](./docs/async-mode.md): Details how to configure and use the asynchronous, polling-based workflow for long-running jobs.
    -   [`deployment.md`](./docs/deployment.md): Provides instructions on how to package your model service into a Docker container for deployment.
-   **API and Configuration**
    -   [`api-reference.md`](./docs/api-reference.md): Offers a detailed reference for all API endpoints, including the new `/service/download/{job_id}` route.
    -   [`input-output.md`](./docs/input-output.md): Shows examples of the JSON schemas used for API requests and responses.
    -   [`configuration.md`](./docs/configuration.md): Lists all the environment variables that can be used to configure the service's behavior.
-   **Support**
    -   [`troubleshooting.md`](./docs/troubleshooting.md): Provides solutions and guidance for common issues and errors.

<!-- Links -->

[OpenAD toolkit]: https://github.com/acceleratedscience/openad-toolkit
[OpenAD model service]: https://openad.accelerate.science/docs/model-service/available-models
