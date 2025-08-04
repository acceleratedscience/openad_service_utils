# Model Selection and Switching Logic

The model wrapper uses a combination of the `service_type` and `service_name` fields in the input JSON to select the appropriate model for a given request.

## Model Selection

When a request is received, the wrapper first looks at the `service_type` to determine whether the request is for property prediction or data generation.

### Property Prediction

For property prediction, the wrapper uses the `service_type` (e.g., `molecule`, `protein`, `crystal`) and the `service_name` to look up the appropriate predictor in the `PropertyPredictorRegistry`.

### Data Generation

For data generation, the wrapper uses the `service_type` (`generate_data`) and the `service_name` to look up the appropriate generator in the `GeneratorRegistry`.

## Dynamic Model Switching

The model wrapper can be configured to use different models for the same `service_type` and `service_name` based on the other parameters in the request. This is achieved by registering multiple models with the same `service_type` and `service_name` but with different parameter schemas.

For example, you could have two different models for predicting the `solubility` property of a molecule, one that uses a simple linear regression model and another that uses a more complex deep learning model. The wrapper would select the appropriate model based on the other parameters in the request, such as the `model_type` parameter.
