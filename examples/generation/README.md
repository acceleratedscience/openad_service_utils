# How to create a Generation Model

## Using Simple implementation (recommended)
follow the [simple_implementation.py](examples/generation/simple_implementation.py) example

<!-- ### steps -->
1. name your class appropriately to your application
    ```python
    class YourModelApplication(SimpleGenerator):
        ...
    ```
2. add the params for s3 download path. path looks like the following `algorithm_type/algorithm_name/algorithm_application/algorithm_version`

    ```python
    algorithm_type: str = "conditional_generation"
    algorithm_name = "MyGeneratorAlgorithm"
    algorithm_version: str = "v0"
    domain: str = "materials"
    ```
3. Implement the generator function to return your models output
    ```python
    def setup_model(self) -> List[Any]:
        ...
    ```
4. call the register function on your application and start the server.
    ```python
    YourModelApplication.register()
    # start the server
    from openad_service_utils import start_server
    start_server(port=8080)
    ```
5. Test your api with the openad-toolkit cli. assuming server is localhost
    ```bash
    catalog model service from remote 'http://localhost:8080' as 'mymodel'
    ```
5. Test your api with using curl. assuming server is localhost
    ```bash
    curl --request GET \
    --url http://localhost:8080/service \
    --header 'Content-Type: application/json'
    ```