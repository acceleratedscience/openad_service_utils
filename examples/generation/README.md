# How to create a Generation Model

## Using Simple implementation (recommended)
follow the [simple_implementation.py](/examples/generation/simple_implementation.py) example


```python
from openad_service_utils import SimpleGenerator
from typing import List, Any


class YourApplicationName(SimpleGenerator):
    # necessary s3 paramters
    algorithm_type: str = "conditional_generation"
    algorithm_name = "MyGeneratorAlgorithm"
    algorithm_application: str = "MySimpleGenerator"
    algorithm_version: str = "v0"
    # your custom api paramters
    actual_parameter1: float = 1.61
    actual_parameter2: float = 1.61

    def setup(self) -> List[Any]:
        # load model
        pass

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

## Generation Models Cache

location based off the template schema

`~/.gt4sd / algorithms / algorithm_type / algorithm_name / algorithm_application / algorithm_version`


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