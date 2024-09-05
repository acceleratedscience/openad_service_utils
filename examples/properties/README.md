# How to create a Properties Model

## Using Simple implementation (recommended)
follow the [simple_implementation.py](/examples/properties/implementation.py) example

```python
from openad_service_utils import SimplePredictor, PredictorTypes, PropertyInfo
from typing import Optional, List, Any


class YourApplicationName(SimplePredictor):
    # necessary s3 paramters
    domain: str = "molecules"
    algorithm_name = "MyAlgorithm"
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

    def predict(sample: Any):
        # setup model prediction
        pass


# register model outside of if __name__ == "__main__"
YourApplicationName.register()

if __name__ == "__main__":
    from openad_service_utils import start_server
    # start the server
    start_server()
```

## Property Models Cache

location based off the template schema

`~/.gt4sd / properties / domain / algorithm_name / algorithm_application / algorithm_version`

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