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
    # the keywords that map to the s3 bucket location for model
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "mypredictor"
    algorithm_application: str = "classification"  # this is also used for api call.
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE

    # OPTIONAL (available_properties). Use only if your class implements many models the user can choose from.
    available_properties = ["property1", "property2"]

    # user proviced params for api / model inference
    temperature: float = Field(description="temperature", default=0.7)
    ...
    ```
3. Implement the `setup_model` function to return your models output
    ```python
    def setup_model(self):
        # load model
        model_path = self.get_model_location()  # function to get model files path
        selected_property = self.get_selected_property() # OPTIONAL. The selected property from (var::available_properties)
        def informative_model(samples) -> List[Any]:
            # run predictions on your model
            return [1,0,1]
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