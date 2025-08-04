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
        pass

    def predict(self, sample: Any):
        # Your prediction logic here
        pass

MySimplePredictor.register()

if __name__ == "__main__":
    from openad_service_utils import start_server
    start_server()
```

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
        pass

    def predict(self, samples: list) -> List[Any]:
        # Your generation logic here
        pass

MySimpleGenerator.register()

if __name__ == "__main__":
    from openad_service_utils import start_server
    start_server()
```

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
    domain: DomainSubmodule = DomainSubmodule.molecules
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
