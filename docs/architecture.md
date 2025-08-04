# Model Wrapper Architecture Overview

This document provides an overview of the model wrapper's architecture. The wrapper is designed to be a flexible and extensible platform for serving machine learning models.

Requests are sent to the model wrapper API using a client, such as the [OpenAD Toolkit](https://github.com/acceleratedscience/openad-toolkit).

## User Flow

The following diagram illustrates the typical user flow:

```mermaid
sequenceDiagram
    participant User
    participant OpenAD Toolkit Client
    participant Model Wrapper API
    participant Model

    User->>OpenAD Toolkit Client: Submits request (e.g., predict solubility)
    OpenAD Toolkit Client->>Model Wrapper API: Sends formatted JSON request
    Model Wrapper API->>Model: Loads model (if not cached)
    Model Wrapper API->>Model: Calls predict/generate method
    Model-->>Model Wrapper API: Returns result
    Model Wrapper API-->>OpenAD Toolkit Client: Sends JSON response
    OpenAD Toolkit Client-->>User: Displays result
```

## Code Flow

The following diagram illustrates the code flow within the model wrapper:

```mermaid
graph TD
    A[Incoming Request] --> B["API Server (server.py)"];
    B --> C["Job Manager"];
    C --> D["Registry (Property/Generator)"];
    D --> E{"Model Cached?"};
    E -- No --> F["Download from AWS S3"];
    F --> G["Cache Model"];
    E -- Yes --> G;
    G --> H["Instantiate & Setup Model"];
    H --> I["Run Inference"];
    I --> J[Result];
    J --> B;
    B --> K[User];
```

## Components

The model wrapper consists of the following key components:

*   **Wrapper API:** The front-facing API that handles incoming requests and routes them to the appropriate model.
*   **Model Loading:** The component responsible for loading models into memory and preparing them for inference.
*   **Generation Modes:** The different modes in which the model can be run, such as prediction, generation, and nested properties.
*   **Inference Pipeline:** The sequence of steps that are executed to perform inference on a given input.
