# new_model_implementation.py

from typing import List, Dict, Any
from openad_service_utils.template.base_classes import BaseGenerator, BaseAlgorithm, BaseConfiguration
from dataclasses import field
from openad_service_utils.algorithms.registry import ApplicationsRegistry

class MyGenerator(BaseGenerator):
    """model implementation"""
    def __init__(self, resources_path: str, param1: int, param2: float):
        super().__init__(resources_path)
        self.param1 = param1
        self.param2 = param2

    def generate(self) -> List[Any]:
        # Implement the generation logic for the new model
        return [1]


class MyGeneratorAlgorithm(BaseAlgorithm[Dict[str, Any], str]):
    """Registry model name"""
    pass


@ApplicationsRegistry.register_algorithm_application(MyGeneratorAlgorithm)
class MyModelGenerator(BaseConfiguration[Dict[str, Any], str]):
    """my model implementation"""
    # define parameters for registry
    algorithm_type: str = "conditional_generation"
    domain: str = "materials"
    algorithm_version: str = "v0"

    # define model parameters
    param1: int = field(default=10, metadata=dict(description="Description of param1"))
    param2: float = field(default=0.5, metadata=dict(description="Description of param2"))

    def get_target_description(self) -> Dict[str, str]:
        return {
            "title": "Target Description",
            "description": "Description of the target for this model",
            "type": "string",
        }

    def get_conditional_generator(self, resources_path: str) -> MyGenerator:
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