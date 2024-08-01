# How to create a Generation Model

## Using Simple implementation (recommended)
follow the [simple_implementation.py](examples/generation/simple_implementation.py) example

<!-- ### steps -->
1. name your application and inheret `SimpleGenerator`
    ```python
    class YourModelApplication(SimpleGenerator):
        ...
    ```
2. add the params for s3 download path. path looks like the following `algorithm_type/algorithm_name/algorithm_application/algorithm_version`

    ```python
    algorithm_type: str = "conditional_generation"
    algorithm_name = "MyGeneratorAlgorithm"
    algorithm_version: str = "v0"

    # user proviced params for api / model inference
    temperature: float = Field(description="temperature", default=0.7)
    ...
    ```
3. Implement the `setup_model` function to return your models output
    ```python
    def setup_model(self) -> List[Any]:
        ...
        return []
    ```
4. call the register function on your application and start the server.
    ```python
    YourModelApplication.register()
    if __name__ == "__main__":
        from openad_service_utils import start_server
        # start the server
        start_server()
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