# How to create a Properties Model

## Using Simple implementation (recommended)
follow the [simple_implementation.py](examples/properties/implementation.py) example

<!-- ### steps -->
1. name your application and inherit `SimplePredictor`
    ```python
    class YourModelApplication(SimplePredictor):
        ...
    ```
2. add the params for s3 download path. path looks like the following `domain/algorithm_name/algorithm_application/algorithm_version`

    ```python
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "mypredictor"
    algorithm_application: str = "classification"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE

    # user proviced params for api / model inference
    temperature: float = Field(description="temperature", default=0.7)
    ...
    ```
3. Implement the `setup_model` function to return your models output
    ```python
    def setup_model(self):
        # load model to device
        def informative_model(samples) -> List[Any]:
            # run predictions on your model
            return predictions
        # return the predictions function to the backend
        return informative_model
    ```
4. call the register function on your application and start the server.
    ```python
    YourModelApplication.register()
    # start the server
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