# Troubleshooting Guide

This guide provides solutions to common issues you may encounter when using the model wrapper.

## Model Not Loading

If the model is not loading, check the following:

*   **Model Path:** Ensure that the `algorithm_type`, `algorithm_name`, `algorithm_application`, and `algorithm_version` in your model's implementation file are correct. These parameters determine the path where the model is stored on disk.
*   **On-Disk Location:** By default, models are cached in the `~/.openad_models` directory. The full path is constructed as follows:
    *   **Properties:** `~/.openad_models/properties/<domain>/<algorithm_name>/<algorithm_application>/<algorithm_version>`
    *   **Generation:** `~/.openad_models/algorithms/<algorithm_type>/<algorithm_name>/<algorithm_application>/<algorithm_version>`
*   **Model Files:** Verify that the model files exist at the specified path and that the user running the service has the necessary permissions to access them.
*   **Dependencies:** Make sure that all the required dependencies for the model are installed in the correct environment.

## Bad Input

If you are getting errors related to bad input, check the following:

*   **Input Schema:** Ensure that your input JSON conforms to the schema described in the [Input/Output Schema Examples](./input-output.md) documentation.
*   **Data Types:** Verify that the data types of your input values are correct. For example, if the model expects a float, make sure you are not passing a string.
*   **Input Values:** Check for any invalid or out-of-range input values.

## Crash Loops

If the service is stuck in a crash loop, check the following:

*   **Logs:** Examine the service logs for any error messages or stack traces that can help you identify the cause of the crash.
*   **Resources:** Ensure that the server has enough memory and CPU resources to run the model.
*   **Configuration:** Review the service configuration to make sure that all the parameters are set correctly.
