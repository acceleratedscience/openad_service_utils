# new_model_implementation.py

###  Rename the base classes [ BaseGenerator, BaseAlgorithm, BaseConfiguration ] and configure
###  Model checkpoints and files need to be bootstraped by the naming scheme to a path
###  schema:    algorithm_type / algorithm_name / algorithm_application / algorithm_version ]
###  exmaple:   conditional_generation / MyGeneratorAlgorithm / MyGenerator / v0


from typing import List, Dict, Any
from dataclasses import field
# from openad_service_utils import BaseConfiguration  # model scaffold
from openad_service_utils.implementation.models import BaseImplementationGenerator


# register the algorithm to the config that returns your model implementation
class MyModelGenerator(BaseImplementationGenerator):
    """model implementation description"""
    # metadata parameters for registry to fetch models from s3
    algorithm_type: str = "conditional_generation"
    algorithm_name = "MyGeneratorAlgorithm"
    algorithm_version: str = "v0"
    domain: str = "materials"

    # define model parameters as fields
    param1: int = field(default=10, metadata=dict(description="Description of param1"))
    param2: float = field(default=0.5, metadata=dict(description="Description of param2"))

    def generate(self) -> List[Any]:
        """Implement the generation logic for the new model

        Returns:
            List[Any]: return your predictions
        """
        # Implement the generation logic for the new model
        # return value must be an iterable List
        return [{"pred1":1, "pred2": 2}]
