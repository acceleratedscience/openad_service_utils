# API Reference

This document provides a detailed reference for the model wrapper API.

## Endpoints

The model wrapper exposes a single endpoint, `/service`, which supports both `GET` and `POST` requests.

---

### `GET /service`

Retrieves the service definitions for all registered models. This is useful for discovering the available models and their parameters.

**Request:**
*   **Method:** `GET`
*   **Endpoint:** `/service`
*   **Body:** None

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON array of service definition objects. Each object contains information about a registered model, including its `service_name`, `service_type`, and the parameters it accepts.

---

### `POST /service`

Submits a job to the model wrapper for processing.

**Request:**
*   **Method:** `POST`
*   **Endpoint:** `/service`
*   **Body:** A JSON object with the following fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `service_type` | string | Yes | The type of service to be called. See [API Request Types](#api-request-types) for a list of available service types. |
| `service_name` | string | Yes | The name of the model to be used. |
| `parameters` | object | Yes | An object containing the parameters for the model. The required parameters will vary depending on the `service_type` and `service_name`. |

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object containing the results of the request. The structure of the response will vary depending on the `service_type` of the request. See the [Input/Output Schema Examples](./input-output.md) for examples.

---

## API Request Types

The `service_type` field in the `POST /service` request body determines the type of job to be executed. The following table lists the available service types and their descriptions.

| `service_type` | Description |
| --- | --- |
| `get_protein_property` | Predicts properties of a protein. |
| `get_molecule_property` | Predicts properties of a molecule. |
| `get_crystal_property` | Predicts properties of a crystal. |
| `generate_data` | Generates new data. |
| `get_result` | Retrieves the results of a previously submitted asynchronous job. |
