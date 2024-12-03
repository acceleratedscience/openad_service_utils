# How to create a Generation Model

## Using Simple implementation (recommended)
follow the [simple_implementation.py](/examples/generation/simple_implementation.py) example


```python
from openad_service_utils import SimpleGenerator
from typing import List, Any
NO_MODEL = False
class YourApplicationName(SimpleGenerator):
    # necessary s3 paramters
    algorithm_type: str = "conditional_generation"
    algorithm_name: str = "MyGeneratorAlgorithm"
    algorithm_application: str = "MySimpleGenerator"
    algorithm_version: str = "v0"
    # your custom api paramters
    actual_parameter1: float = 1.61
    actual_parameter2: float = 1.61

    def setup(self) -> List[Any]:
        # load model
        pass
    
    # if No Model is set to true do not try and ensure the Model artifacts are available to Run
    def ensure_artifacts(self):
        global NO_MODEL
        if NO_MODEL:
            return "no model"
        else:
            return super().ensure_artifacts()

    def predict(self, sample: Any | None = None):
        # setup model prediction
        pass


# register model outside of if __name__ == "__main__"
YourApplicationName.register()

if __name__ == "__main__":
    from openad_service_utils import start_server
    # start the server
    start_server()
```

## NO_MODEL Global Variable
This global variable in the Implementation example allows you to run the service without the automatic loading of models. This is a useful option when you are wrapping an API like provided in RDKIT for generating properties or if you want to create a Pipeline that calls different models from other services. <br>

By Default for standard Model inference it should be set to `FALSE`


## Generation Models Cache

location based off the template schema

`~/.openad_models / algorithms / algorithm_type / algorithm_name / algorithm_application / algorithm_version`


## Test your api with the openad-toolkit cli. assuming server is localhost
```bash
>> catalog model service from remote 'http://localhost:8080' as 'mygenerator'
>> mygenerator ?
```

## Test your api with using curl. assuming server is localhost
```bash
curl --request GET \
--url http://localhost:8080/service \
--header 'Content-Type: application/json'
```




## Detailed Example of a Generation with no Model

```python
# simple_implementation.py

###  Name the child class of SimpleGenerator as you model application and configure
###  Model checkpoints and files need to be bootstraped by the naming scheme to a path

from typing import List, Any
from pydantic.v1 import Field
from openad_service_utils import SimpleGenerator
from time import sleep

NO_MODEL = True  # if you are simply providind an api to generate a data set then use false , otherwide True

class MyModel:
    def __init__(self, x) -> None:
        pass

    def net(self, x):
        pass

# register the algorithm to the config that returns your model implementation
class MySimpleGenerator(SimpleGenerator):
    """model implementation description"""

    # metadata parameters for registry to fetch models from s3
    # s3 path: algorithm_type / algorithm_name / algorithm_application / algorithm_version
    algorithm_type: str = "conditional_generation"
    algorithm_name: str = "MyGeneratorAlgorithm"
    algorithm_application: str = "MySimpleGenerator"
    algorithm_version: str = "v0"

    # define model parameters as fields for the api
    batch_size: int = Field(description="Prediction batch size", default=128)
    temperature: float = Field(description="Temperature", default=0.7)

    def setup(self):
        print(">> model filepath: ", self.get_model_location())  # load model
        self.model_path = self.get_model_location()
        self.model = MyModel(self.model_path)
        return

    # if No Model is set to true do not try and ensure the Model artifacts are available to Run
    def ensure_artifacts(self):
        global NO_MODEL
        if NO_MODEL:
            return "no model"
        else:
            return super().ensure_artifacts()

    def predict(self, samples: list) -> List[Any]:
        """Implement the generation logic for the new model
        Returns:
            List[Any]: return your predictions
        """
        # Implement the generation logic for the model, This is cancelled out as Example is using NO_MODEL=True
        # self.model.net(self.temperature)
        
        # return value must be an iterable
        return [{"pred1": 1, "pred2": 2}]

```