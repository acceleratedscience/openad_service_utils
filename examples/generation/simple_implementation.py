# simple_implementation.py

###  Name the child class of SimpleGenerator as you model application and configure
###  Model checkpoints and files need to be bootstraped by the naming scheme to a path

from typing import List, Any
from dataclasses import field
from openad_service_utils import SimpleGenerator


# register the algorithm to the config that returns your model implementation
class MySimpleGenerator(SimpleGenerator):
    """model implementation description"""
    # metadata parameters for registry to fetch models from s3
    #   schema:    algorithm_type / algorithm_name / algorithm_application / algorithm_version
    #   downloads model using prefix: algorithm/(algorithm_type)/(algorithm_name)/MySimpleGenerator/(algorithm_version)
    algorithm_type: str = "conditional_generation"
    algorithm_name = "MyGeneratorAlgorithm"
    algorithm_version: str = "v0"
    domain: str = "materials"

    # define model parameters as fields for the api
    param1: int = field(default=10, metadata=dict(description="Description of param1"))
    param2: float = field(default=0.5, metadata=dict(description="Description of param2"))

    def setup_model(self) -> List[Any]:
        """Implement the generation logic for the new model

        Returns:
            List[Any]: return your predictions
        """
        # Implement the generation logic for the new model
        # return value must be an iterable
        print(">> model filepath: ", self.get_model_location())  # load model
        self.model_path = self.get_model_location()
        return [{"pred1":1, "pred2": 2}]
