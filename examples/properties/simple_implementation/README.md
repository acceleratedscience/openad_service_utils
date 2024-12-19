# How to create a Properties Model

## Using Simple implementation (recommended)
follow the [simple_implementation.py](/examples/properties/implementation.py) example

```python
from openad_service_utils import SimplePredictor, PredictorTypes, PropertyInfo
from typing import Optional, List, Any
from openad_service_utils.common.algorithms.core import AlgorithmConfiguration


class YourApplicationName(SimplePredictor):
    # necessary s3 paramters
    domain: str = "molecules"
    algorithm_name: str = "MyAlgorithm"
    algorithm_application: str = "mypredictor"
    algorithm_version: str = "v0"
    # necessary api types to define
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    available_properties: Optional[List[PropertyInfo]] = []
    # your custom api paramters
    some_parameter1: float = 1.61
    some_parameter2: float = 1.61

    def setup(self) -> List[Any]:
        # load model
        pass

    def get_predictor(self, configuration: AlgorithmConfiguration):
        """overwrite existing function to download model only once"""
        global NO_MODEL
        if NO_MODEL is False:
            super().get_predictor(self)
        else:
            print("no predictor")

    def predict(sample: Any):
        # setup model prediction
        pass


# register model outside of if __name__ == "__main__"
#no_model Defaults to flase, if set to true it will not attempt to pull any stred mode lcheckpoints
YourApplicationName.register(no_model=True)

if __name__ == "__main__":
    from openad_service_utils import start_server
    # start the server
    start_server()
```

## no_model Class register parameter
This parameters in the Implementation example allows you to run the service without the automatic loading of models. This is a useful option when you are wrapping an API like provided in RDKIT for generating properties or if you want to create a Pipeline that calls different models from other services. <br>
By Default for standard Model inference is set to `False`<br>

e.g.<br>
To auto Load a model from given path: <br>
```Python 
MySimplePredictor.register( no_model=False)
```

<br>
e.g.<br>
To Not auto Load a model from given path so that you can use API or other loading method:  <br>

```Python 
MySimplePredictor.register( no_model=True)
```

## Property Models Cache

location based off the template schema

`~/.openad_models / properties / domain / algorithm_name / algorithm_application / algorithm_version`

## Test your api with the openad-toolkit cli. assuming server is localhost
```bash
>> catalog model service from remote 'http://localhost:8080' as 'mypredictor'
>> mypredictor ?
```

## Test your api with using curl. assuming server is localhost
```bash
curl --request GET \
--url http://localhost:8080/service \
--header 'Content-Type: application/json'
```