# new_model_implementation.py

###  Rename the base classes [ BaseGenerator, BaseAlgorithm, BaseConfiguration ] and configure
###  Model checkpoints and files need to be bootstraped by the naming scheme to a path
###  schema:    algorithm_type / algorithm_name / algorithm_application / algorithm_version ]
###  exmaple:   conditional_generation / MyGeneratorAlgorithm / MyGenerator / v0


from typing import List, Dict, Any
from dataclasses import field
from openad_service_utils import BaseGenerator, BaseAlgorithm, BaseConfiguration  # model scaffold


class MyGenerator(BaseGenerator):
    """model implementation"""
    def __init__(self, resources_path: str, param1: int, param2: float):
        super().__init__(resources_path)
        self.param1 = param1
        self.param2 = param2

    def generate(self) -> List[Any]:
        """Implement the generation logic for the new model

        Returns:
            List[Any]: return your predictions
        """
        # Implement the generation logic for the new model
        # return value must be an iterable List
        return [{"pred1":1, "pred2": 2}]


class MyGeneratorAlgorithm(BaseAlgorithm[Dict[str, Any], str]):
    """Registry algorithm name"""
    pass


# register the algorithm to the config that returns your model implementation
class MyClassicGenerator(BaseConfiguration[Dict[str, Any], str]):
    """model implementation description"""
    # metadata parameters for registry to fetch models from s3
    algorithm_type: str = "conditional_generation"
    domain: str = "materials"
    algorithm_version: str = "v0"
    algorithm_class = MyGeneratorAlgorithm

    # define model parameters as fields
    param1: int = field(default=10, metadata=dict(description="Description of param1"))
    param2: float = field(default=0.5, metadata=dict(description="Description of param2"))

    def get_target_description(self) -> Dict[str, str]:
        """describe the target for this model"""
        # can do without a target and pass all vars to init params
        return {
            "title": "Target Description",
            "description": "Description of the target for this model",
            "type": "string",
        }

    def get_conditional_generator(self, resources_path: str) -> MyGenerator:
        """returns your model implementation"""
        return MyGenerator(
            resources_path=resources_path,
            param1=self.param1,
            param2=self.param2,
        )


if __name__ == "__main__":
    config = MyModelGenerator()
    algorithm = MyGeneratorAlgorithm(configuration=config, target=None)
    gen = algorithm.sample(1)
    print(list(gen))