# Sample Configuration Templates

This document provides sample configuration templates for common use cases.

## Property Prediction

This template shows how to configure a simple property predictor.

```python
from openad_service_utils import SimplePredictor, PredictorTypes, PropertyInfo, DomainSubmodule
from typing import Optional, List, Any

class MySimplePredictor(SimplePredictor):
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "MyAlgorithm"
    algorithm_application: str = "mypredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    available_properties: Optional[List[PropertyInfo]] = [
        PropertyInfo(name="LogP", description=""),
        PropertyInfo(name="TPSA", description=""),
    ]

    def setup(self) -> List[Any]:
        # Load your model here
        # self.get_model_location() will return the path to the model's cached directory.
        # You can use this to load your model files.
        # For example:
        # self.model = MyModel.load(self.get_model_location())
        pass

    def predict(self, sample: Any):
        # Your prediction logic here
        pass

MySimplePredictor.register()

if __name__ == "__main__":
    from openad_service_utils import start_server
    start_server()
```

### Working with Models Not Stored in AWS S3

By default, the model wrapper assumes that your model is stored in an AWS S3 bucket and will attempt to download and cache it. If your model is loaded from a different source, such as HuggingFace Hub or a local file path, you can prevent this behavior by passing `no_model=True` to the `register` method.

```python
MySimplePredictor.register(no_model=True)
```

When `no_model=True` is used, the wrapper will not attempt to download any model files from S3. You are then responsible for loading the model in the `setup` method.

## Data Generation

This template shows how to configure a simple data generator.

```python
from openad_service_utils import SimpleGenerator
from typing import List, Any

class MySimpleGenerator(SimpleGenerator):
    algorithm_type: str = "conditional_generation"
    algorithm_name: str = "MyGeneratorAlgorithm"
    algorithm_application: str = "MySimpleGenerator"
    algorithm_version: str = "v0"

    def setup(self) -> List[Any]:
        # Load your model here
        # self.get_model_location() will return the path to the model's cached directory.
        # You can use this to load your model files.
        # For example:
        # self.model = MyModel.load(self.get_model_location())
        pass

    def get_target_description(self) -> dict | None:
        """Get description of the target for generation."""
        return {
            "title": "Target",
            "type": "string",
            "description": "A string to use as a starting point for generation.",
        }

    def predict(self, samples: list) -> List[Any]:
        # Your generation logic here
        pass

MySimpleGenerator.register()

if __name__ == "__main__":
    from openad_service_utils import start_server
    start_server()
```

### Working with Models Not Stored in AWS S3

Similar to property predictors, if your generation model is loaded from a source other than AWS S3 (e.g., HuggingFace Hub or a local file path), you can prevent the wrapper from attempting to download and cache it by passing `no_model=True` to the `register` method.

```python
MySimpleGenerator.register(no_model=True)
```

When `no_model=True` is used, the wrapper will not attempt to download any model files from S3. You are then responsible for loading the model in the `setup` method.


## Nested Properties and Multiple Models

This section explains how to configure a service that uses multiple models or has a complex, nested parameter structure. This is useful when you want to group related models under a single service or when a model requires a hierarchical configuration.

The key idea is to separate the parameter definitions from the main predictor class. You can define one or more parameter classes that inherit from `PropertyPredictorParameters` and then pass an instance of a parameter class to the `register` method of your predictor class.

### 1. Define Parameter Classes

Create a separate Python file (e.g., `my_app_parameters.py`) to define your parameter classes. Each class should inherit from `PropertyPredictorParameters` and define the parameters for a specific model or group of models.

```python
# my_app_parameters.py
from openad_service_utils import PropertyPredictorParameters, DomainSubmodule, PredictorTypes, PropertyInfo
from pydantic.v1 import Field

class ToxicityModelParams(PropertyPredictorParameters):
    """Parameters for toxicity prediction models."""
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "ToxicityPredictor"
    algorithm_application: str = "general"
    algorithm_version: str = "v1"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    available_properties: list[PropertyInfo] = [
        PropertyInfo(name="LD50", description="Lethal dose for 50% of subjects."),
        PropertyInfo(name="LC50", description="Lethal concentration for 50% of subjects."),
    ]
    model_backend: str = Field(description="The computational backend for the model.", default="cpu")

    def set_parameters(self, **kwargs):
        """Overwrite default parameters"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
```

### 2. Create a Predictor Class

Create a predictor class as usual. This class can be a generic predictor that is configured at runtime by the parameter classes.

```python
# implementation.py
from openad_service_utils import SimplePredictor
from typing import Any

class MyPredictor(SimplePredictor):
    def setup(self):
        print(f"Setting up model: {self.algorithm_name}/{self.algorithm_application} on {self.model_backend}")
        # Your model setup logic here
        pass

    def predict(self, sample: Any):
        # Your prediction logic here
        pass
```

### 3. Register the Predictor with Different Parameters

In your main script, you can register the same predictor class multiple times with different parameter configurations.

```python
# run_server.py
from implementation import MyPredictor
from my_app_parameters import ToxicityModelParams
from openad_service_utils import start_server

# Register a CPU-based toxicity model
cpu_params = ToxicityModelParams()
MyPredictor.register(cpu_params)

# Register a GPU-based toxicity model
gpu_params = ToxicityModelParams()
gpu_params.set_parameters(
    algorithm_application="high_performance",
    model_backend="gpu"
)
MyPredictor.register(gpu_params)


if __name__ == "__main__":
    start_server()
```

This approach allows you to create a flexible and modular service that can support multiple models and complex parameter configurations under a single, reusable predictor class.

## Mesh Property Prediction

This template demonstrates how to configure a mesh property predictor that accepts VTK files via the `/service/upload` endpoint.

```python
from openad_service_utils import SimplePredictor, PredictorTypes, PropertyInfo, DomainSubmodule
from typing import List, Any, Dict, Union, Optional
import ast
import trimesh
import os
import pyvista as pv

class MyMeshPredictor(SimplePredictor):
    domain: DomainSubmodule = DomainSubmodule.meshes
    algorithm_name: str = "MeshGraphTransformer"
    algorithm_application: str = "surface_property_prediction"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MESH
    available_properties: Optional[List[PropertyInfo]] = [
        PropertyInfo(name="SurfaceArea", description="Predicted surface area of the mesh."),
        PropertyInfo(name="Volume", description="Predicted volume enclosed by the mesh."),
    ]

    def setup(self):
        print(f"Setting up Mesh predictor: {self.algorithm_name}/{self.algorithm_application}")

    def predict(self, input: Union[str, List[str]]) -> Dict[str, Any]:
        print(f"Received sample for prediction: {input}")
        
        file_paths: List[str] = []
        if isinstance(input, str):
            file_paths.append(input)
        elif isinstance(input, list) and all(isinstance(s, str) for s in input):
            file_paths = input
        else:
            raise ValueError("Input sample must be a file path string or a list of file path strings.")

        results: Dict[str, Any] = {}
        for file_path in file_paths:
            print(f"Loading mesh from file: {file_path}")
            try:
                # Load the VTK file using pyvista
                pv_mesh = pv.read(file_path)
                
                # Convert pyvista mesh to trimesh mesh
                trimesh_mesh = trimesh.Trimesh(vertices=pv_mesh.points, faces=pv_mesh.faces.reshape(-1, 4)[:, 1:])
                
                # Perform prediction based on selected_property
                if self.selected_property == "SurfaceArea":
                    prediction_result = trimesh_mesh.area
                elif self.selected_property == "Volume":
                    prediction_result = trimesh_mesh.volume
                else:
                    prediction_result = f"Property {self.selected_property} not supported by this predictor."
                
                results[file_path] = {
                    "property": self.selected_property,
                    "result": prediction_result
                }
            except Exception as e:
                results[file_path] = {
                    "property": self.selected_property,
                    "error": f"Error loading or processing mesh from file {file_path}: {str(e)}"
                }
        
        return results

MyMeshPredictor.register(no_model=True)

if __name__ == "__main__":
    from openad_service_utils import start_server
    start_server()
```

### Using the `/service/upload` Endpoint for File Input

For predictors that require file inputs, such as the `MyMeshPredictor` which processes VTK files, you can use the `/service/upload` endpoint to upload your files and obtain a `file_key`. This `file_key` can then be included in your `POST /service` request.

**1. Upload your file:**

Send a `POST` request to `/service/upload` with your file as `multipart/form-data`.

```bash
curl -X POST "http://localhost:8080/service/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/your/dec.vtk;type=application/octet-stream"
```

The response will contain a `file_key`:

```json
{
  "file_key": "e490e8e4-58c7-425b-9251-563aa880a0ce",
  "message": "File uploaded successfully."
}
```

**2. Use the `file_key` in your `/service` request:**

Include the obtained `file_key` in the `file_keys` array of your `POST /service` request.

```json
{
  "service_type": "get_mesh_property",
  "service_name": "get mesh surface_property_prediction",
  "parameters": {
    "property_name": "SurfaceArea"
  },
  "file_keys": ["e490e8e4-58c7-425b-9251-563aa880a0ce"]
}
```

The server will use the `file_key` to retrieve the uploaded file from its temporary storage (Redis) and pass its path to your predictor's `predict` method. If a `file_key` is not found in Redis, the server will return a 404 error.
