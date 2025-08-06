# Input/Output Schema Examples

This document provides examples of the input and output schemas for the model wrapper's API.

## Input Schema

The API expects a JSON object with a `service_type` and `service_name` field that determines which model to use. The `parameters` field contains the inputs for the model.

### Property Prediction

For property prediction, the `service_type` should be one of the values from the `PredictorTypes` enum: `get_protein_property`, `get_molecule_property`, or `get_crystal_property`. The `parameters` object must contain `property_type` (a list of properties to predict) and `subjects` (a list of inputs to predict on). Additional parameters may be required depending on the specific model.

**Example:**

```json
{
  "service_type": "get_molecule_property",
  "service_name": "MySimplePredictor",
  "parameters": {
    "property_type": ["LogP", "TPSA"],
    "subjects": ["CCO", "CCC"]
  }
}
```

### Data Generation

For data generation, the `service_type` should be `generate_data`. The `parameters` object can contain `subjects` (to be used as a starting point for generation) and other parameters specific to the generator.

**Example:**

```json
{
  "service_type": "generate_data",
  "service_name": "MySimpleGenerator",
  "parameters": {
    "n_samples": 10,
    "subjects": ["c1ccccc1"]
  }
}
```

### Asynchronous Job Submission

To submit a job for asynchronous processing, add the `"async": true` field to any Property Prediction or Data Generation request.

**Example:**
```json
{
  "service_type": "get_molecule_property",
  "service_name": "MySimplePredictor",
  "parameters": {
    "property_type": ["LogP", "TPSA"],
    "subjects": ["CCO", "CCC"]
  },
  "async": true
}
```

### Asynchronous Job Retrieval

To retrieve the results of an asynchronous job, use the `get_result` service type.

**Example:**
```json
{
  "service_type": "get_result",
  "url": "f1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

## Output Schema

The output schema depends on the `service_type` of the request.

### Property Prediction Output

The output is a list of JSON objects, where each object contains the subject, the property, and the predicted result.

```json
[
    {
        "subject": "CCO",
        "property": "LogP",
        "result": -0.0014000000000000123
    },
    {
        "subject": "CCO",
        "property": "TPSA",
        "result": 20.23
    },
    {
        "subject": "CCC",
        "property": "LogP",
        "result": 0.49860000000000003
    },
    {
        "subject": "CCC",
        "property": "TPSA",
        "result": 0
    }
]
```

### Data Generation Output

The output is a list of generated items.

```json
[
    {
        "result": "C1=CC=C(C=C1)C(C)(C)C"
    },
    {
        "result": "CC(C)(C)C1=CC=C(C=C1)C(C)(C)C"
    }
]
```

### Asynchronous Job Submission Output

When you submit an asynchronous job, the server will respond with a job ID.

```json
{
  "job_id": "f1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

### Asynchronous Job Retrieval Output

When you retrieve the results of an asynchronous job, the server will respond with the results of the job, or a status indicating that the job is still pending. If the job is complete, the output will be the same as the corresponding synchronous request.
