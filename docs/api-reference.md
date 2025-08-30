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

Submits a job to the model wrapper for processing. The structure of the request body depends on the `service_type`.

#### Property Prediction and Data Generation

Used for submitting synchronous or asynchronous jobs for property prediction or data generation.

**Request Body:**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `service_type` | string | Yes | One of `get_protein_property`, `get_molecule_property`, `get_crystal_property`, `get_mesh_property`, or `generate_data`. |
| `service_name` | string | Yes | The name of the model to be used. |
| `parameters` | object | Yes | An object containing the parameters for the model. |
| `async` | boolean | No | Set to `true` to submit the job for asynchronous processing. |
| `file_keys` | array of strings | No | A list of file keys obtained from the `/service/upload` endpoint, referencing uploaded subject files. |

**Response:**
*   **Synchronous:** A JSON object containing the results of the request. See the [Input/Output Schema Examples](./input-output.md) for examples.
*   **Asynchronous:** A JSON object containing the `job_id`.

#### Asynchronous Job Retrieval

Used for retrieving the results of a previously submitted asynchronous job.

**Request Body:**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `service_type` | string | Yes | Must be `get_result`. |
| `url` | string | Yes | The `job_id` of the asynchronous job to retrieve. |

**Response:**
*   A JSON object containing the results of the job, or a status indicating that the job is still pending.

---

### `POST /service/upload`

Uploads a file to a temporary location on the server and returns a unique `file_key` that can be used in subsequent `/service` requests. This endpoint is used for submitting large or complex input data, such as mesh files, that cannot be directly included in the `POST /service` request body.

**Request:**
*   **Method:** `POST`
*   **Endpoint:** `/service/upload`
*   **Content-Type:** `multipart/form-data`
*   **Body:**
    *   `file`: The file to be uploaded.

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object containing the `file_key` and a success message.
    ```json
    {
      "file_key": "unique-file-identifier",
      "message": "File uploaded successfully."
    }
    ```
