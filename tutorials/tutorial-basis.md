# Foundational Tutorial: Creating a Simple Property Predictor

This tutorial will guide you through the process of creating a simple property predictor using the OpenAD Service Utilities.

## 1. Create a New Python File

Create a new Python file for your predictor. For this tutorial, we will name it `my_predictor.py`.

## 2. Import Necessary Classes

Import the necessary classes from the `openad_service_utils` library.

```python
from openad_service_utils import SimplePredictor, PredictorTypes, PropertyInfo, DomainSubmodule
from typing import Optional, List, Any
from pydantic.v1 import Field
```

## 3. Create a Predictor Class

Create a class for your predictor that inherits from `SimplePredictor`.

```python
class MySimplePredictor(SimplePredictor):
    # ...
```

## 4. Define Model Metadata

Define the metadata for your model. This includes the `domain`, `algorithm_name`, `algorithm_application`, `algorithm_version`, and `property_type`.

```python
class MySimplePredictor(SimplePredictor):
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "MyAlgorithm"
    algorithm_application: str = "mypredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
```

These metadata fields are used to construct the path where the model is stored in AWS S3 and cached locally. The path for this example is constructed as follows: `~/.openad_models/properties/<domain>/<algorithm_name>/<algorithm_application>/<algorithm_version>`.

If your model is not stored in AWS S3, see the [Working with Models Not Stored in AWS S3](#working-with-models-not-stored-in-aws-s3) section.

## 5. Define Available Properties

Define the properties that your model can predict.

```python
class MySimplePredictor(SimplePredictor):
    # ...
    available_properties: Optional[List[PropertyInfo]] = [
        PropertyInfo(name="LogP", description=""),
        PropertyInfo(name="TPSA", description=""),
    ]
```

## 5a. Define Custom Parameters (Optional)

You can expose custom parameters to the user through the API by defining them as class variables using `pydantic.v1.Field`. These parameters will appear in the `parameters` section of the service definition and can be passed in the API request.

```python
class MySimplePredictor(SimplePredictor):
    # ...
    # Define custom parameters
    temperature: float = Field(description="Temperature for the prediction.", default=0.7)
    batch_size: int = Field(description="Batch size for prediction.", default=128)
```

When a user makes a request, they can provide values for these parameters:

```json
{
  "service_type": "get_molecule_property",
  "service_name": "mypredictor",
  "parameters": {
    "property_type": ["LogP"],
    "subjects": ["CCO"],
    "temperature": 0.9,
    "batch_size": 256
  }
}
```

You can then access these values within your `predict` method using `self.temperature` and `self.batch_size`.

## 6. Implement the `setup` Method

Implement the `setup` method to load your model.

```python
class MySimplePredictor(SimplePredictor):
    # ...
    def setup(self) -> List[Any]:
        # Load your model here
        pass
```

## 7. Implement the `predict` Method

Implement the `predict` method to run your model and return the predictions.

```python
class MySimplePredictor(SimplePredictor):
    # ...
    def predict(self, sample: Any):
        # Your prediction logic here
        pass
```

## 8. Register Your Predictor

Register your predictor so that it can be discovered by the service.

```python
MySimplePredictor.register()
```

### Working with Models Not Stored in AWS S3

By default, the model wrapper assumes that your model is stored in an AWS S3 bucket and will attempt to download and cache it. If your model is loaded from a different source, such as HuggingFace Hub or a local file path, you can prevent this behavior by passing `no_model=True` to the `register` method.

```python
MySimplePredictor.register(no_model=True)
```

When `no_model=True` is used, the wrapper will not attempt to download any model files from S3. You are then responsible for loading the model in the `setup` method. This is the case in our `protein_solubility_walkthrough.ipynb` tutorial, where the model is loaded directly from HuggingFace.

## 9. Start the Server

Add the following code to start the server.

```python
if __name__ == "__main__":
    from openad_service_utils import start_server
    start_server()
