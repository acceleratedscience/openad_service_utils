# API Reference

This document provides a detailed reference for the model wrapper API.

## Health & Admin

### `GET /health`

Checks the health of the service.

**Request:**
*   **Method:** `GET`
*   **Endpoint:** `/health`
*   **Body:** None

**Response:**
*   **Content-Type:** `text/html`
*   **Body:** "UP"

---

### `GET /admin/details`

Retrieves server configuration details.

**Request:**
*   **Method:** `GET`
*   **Endpoint:** `/admin/details`
*   **Body:** None

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object containing the server settings.

---

## Service Definition & Execution

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
| `async` | boolean | No | Set to `true` to submit the job for asynchronous processing. See [Execution Workflows](./architecture.md#execution-workflows) for more details. |
| `file_keys` | array of strings | No | A list of file keys in the format `collection_name/filename.ext`, referencing uploaded subject files. |

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
*   A JSON object containing the status of the job. If the job is complete and the result is a file, the response will include a `download_url`. Otherwise, for JSON-based results, it will contain the result data directly.

---

## File Collections

**Note:** The file collection endpoints are only available if the service is configured with a property predictor that supports file collections (i.e., `get_mesh_property`). If not available, these endpoints will return a `404 Not Found` error.

### `GET /service/collections`

Retrieves a list of all available collections.

**Request:**
*   **Method:** `GET`
*   **Endpoint:** `/service/collections`
*   **Body:** None

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object containing a list of collection names.
    ```json
    {
      "collections": ["collection1", "collection2"]
    }
    ```

---

### `POST /service/collections/{collection_name}`

Uploads a file to a specific collection.

**Request:**
*   **Method:** `POST`
*   **Endpoint:** `/service/collections/{collection_name}`
*   **Path Parameters:**
    *   `collection_name` (string, required): The name of the collection.
*   **Content-Type:** `multipart/form-data`
*   **Body:**
    *   `file`: The file to be uploaded.

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object containing the `file_key` and a success message.
    ```json
    {
      "file_key": "collection_name/filename.ext",
      "message": "File uploaded successfully."
    }
    ```

---

### `GET /service/collections/{collection_name}`

Retrieves a list of all files within a specific collection.

**Request:**
*   **Method:** `GET`
*   **Endpoint:** `/service/collections/{collection_name}`
*   **Path Parameters:**
    *   `collection_name` (string, required): The name of the collection.

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object containing a list of file objects, each with a `file_key`, `filename`, and `size_bytes`.
    ```json
    {
      "files": [
        {"file_key": "collection_name/file1.txt", "filename": "file1.txt", "size_bytes": 1024},
        {"file_key": "collection_name/file2.txt", "filename": "file2.txt", "size_bytes": 2048}
      ]
    }
    ```

---

### `GET /service/collections/{collection_name}/{filename}`

Downloads a file from a specific collection.

**Request:**
*   **Method:** `GET`
*   **Endpoint:** `/service/collections/{collection_name}/{filename}`
*   **Path Parameters:**
    *   `collection_name` (string, required): The name of the collection.
    *   `filename` (string, required): The name of the file to download.

**Response:**
*   The binary content of the file.

---

### `DELETE /service/collections/{collection_name}`

Deletes an entire collection and all of its files.

**Request:**
*   **Method:** `DELETE`
*   **Endpoint:** `/service/collections/{collection_name}`
*   **Path Parameters:**
    *   `collection_name` (string, required): The name of the collection to be deleted.

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object with a success message.
    ```json
    {
      "message": "Collection 'collection_name' deleted successfully."
    }
    ```

---

### `DELETE /service/collections/{collection_name}/{filename}`

Deletes a specific file from a collection.

**Request:**
*   **Method:** `DELETE`
*   **Endpoint:** `/service/collections/{collection_name}/{filename}`
*   **Path Parameters:**
    *   `collection_name` (string, required): The name of the collection.
    *   `filename` (string, required): The name of the file to be deleted.

**Response:**
*   **Content-Type:** `application/json`
*   **Body:** A JSON object with a success message.
    ```json
    {
      "message": "File deleted successfully."
    }
    ```

---

## Asynchronous Job Results

### `GET /service/download/{job_id}/{filename}`

Downloads the file result of a completed asynchronous job.

**Request:**
*   **Method:** `GET`
*   **Endpoint:** `/service/download/{job_id}/{filename}`
*   **Path Parameters:**
    *   `job_id` (string, required): The ID of the completed asynchronous job.
    *   `filename` (string, required): The name of the file to download.

**Response:**
*   The binary content of the result file.
