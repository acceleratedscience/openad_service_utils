# Main imports
from typing import List, Any, Dict, Optional, Iterator, TypeVar
from pydantic.v1 import Field
from openad_service_utils import SimpleGenerator, start_server

# Model imports
### -----------------------------------------
### ZONE A - MODEL IMPORTS

import random

### -----------------------------------------


# Register the algorithm with the config that returns your model implementation
class ExampleGenerator(SimpleGenerator):
    """
    Generate 10 entries with dummy data.
    """

    # Registry parameters to fetch model from S3
    # - - -
    # S3 path: algorithm_type / algorithm_name / algorithm_application / algorithm_version
    # Run self.get_model_location() to see the compiled path
    algorithm_type: str = "example_generation"
    algorithm_name: str = "ExampleGeneratorAlgorithm"
    algorithm_application: str = "ExampleGenerator"
    algorithm_version: str = "v0"

    # User-provided parameters for API / model inference
    ### -----------------------------------------
    ### ZONE B - MODEL PARAMETERS

    foo: int = Field(description="Example parameter A", default=100)
    bar: str = Field(description="Example parameter B", default="abc")

    ### -----------------------------------------

    def setup(self):
        ### -----------------------------------------
        ### ZONE C - MODEL INSTANTIATION (empty)
        ### -----------------------------------------
        print(">> Model filepath: ", self.get_model_location())

    # NOTE: Explain better
    # Override target description in this case we put we make the target a list
    def get_target_description(self) -> Optional[Dict[str, str]]:
        """
        Get description of the target for generation.
        If not included, this will use the default value defined in core.py.
        """

        return {
            "title": "TITLE GOES HERE",
            "type": "List / String / Integer / Float / ...",  ### <-- Update
            "description": "DESCRIPTION GOES HERE",  ### <-- Update
        }

    def predict(self, samples: List) -> List[Any]:
        """
        Generation logic for the model.

        Returns:
            List[Any]: ...
        """

        ### -----------------------------------------
        ### ZONE D: INSERT MODEL EXECUTION HERE

        results = []
        for sample in samples:
            for i in range(5):
                results.append(
                    {
                        "target": sample,
                        "index": i,
                        "random_int": random.randint(0, 100),
                        "random_fruit": random.choice(["apple", "banana", "cherry"]),
                    }
                )
        return results

        ### -----------------------------------------


# Model registration
# - - -
# Set no_model to True when you're wrapping something that's not an actual model.
# Eg. if you're simply returning a dataset for testing or otherwise
# --> This skips the step where we ensure the model artifacts are available to run
ExampleGenerator.register(no_model=True)

# Start the server
if __name__ == "__main__":
    start_server(port=8080)
