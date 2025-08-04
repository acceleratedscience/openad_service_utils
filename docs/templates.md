# Sample Configuration Templates

This document provides sample configuration templates for common use cases.

## Property Prediction

This template shows how to configure a simple property predictor.

```python
from openad_service_utils import SimplePredictor, PredictorTypes, PropertyInfo
from typing import Optional, List, Any

class MySimplePredictor(SimplePredictor):
    domain: str = "molecules"
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

## Nested Properties

This template shows how to configure a predictor with nested properties.

```python
from openad_service_utils import SimplePredictor, PredictorTypes, PropertyInfo
from typing import Optional, List, Any
from pydantic.v1 import Field

class MyNestedPredictor(SimplePredictor):
    domain: str = "molecules"
    algorithm_name: str = "MyAlgorithm"
    algorithm_application: str = "mynestedpredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    available_properties: Optional[List[PropertyInfo]] = [
        PropertyInfo(name="all", description=""),
    ]

    # Define nested parameters
    nested_param: str = Field(description="A nested parameter", default="default_value")

    def setup(self) -> List[Any]:
        # Load your model here
        pass

    def predict(self, sample: Any):
        # Your prediction logic here
        pass

MyNestedPredictor.register()

if __name__ == "__main__":
    from openad_service_utils import start_server
    start_server()
```