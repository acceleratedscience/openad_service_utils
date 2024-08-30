# simple_implementation.py

###  Name the child class of SimpleGenerator as you model application and configure
###  Model checkpoints and files need to be bootstraped by the naming scheme to a path

from typing import List, Any
from pydantic.v1 import Field
from openad_service_utils import SimpleGenerator

class MyModel:
    def __init__(self, x) -> None:
        pass
    def net(self, x):
        pass

# register the algorithm to the config that returns your model implementation
class MySimpleGenerator(SimpleGenerator):
    """model implementation description"""
    # metadata parameters for registry to fetch models from s3
    # s3 path: algorithm_type / algorithm_name / algorithm_application / algorithm_version
    algorithm_type: str = "conditional_generation"
    algorithm_name = "MyGeneratorAlgorithm"
    algorithm_application: str = "MySimpleGenerator"
    algorithm_version: str = "v0"

    # define model parameters as fields for the api
    batch_size: int = Field(description="Prediction batch size", default=128)
    temperature: float = Field(description="Temperature", default=0.7)

    def setup(self):
        print(">> model filepath: ", self.get_model_location())  # load model
        self.model_path = self.get_model_location()
        self.model = MyModel(self.model_path)
    
    def predict(self) -> List[Any]:
        """Implement the generation logic for the new model
        Returns:
            List[Any]: return your predictions
        """
        # Implement the generation logic for the model
        self.model.net(self.temperature)
        # return value must be an iterable
        return [{"pred1":1, "pred2": 2}]
