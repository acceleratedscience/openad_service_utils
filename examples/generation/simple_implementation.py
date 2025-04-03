# simple_implementation.py
###  Name the child class of SimpleGenerator as you model application and configure
###  Model checkpoints and files need to be bootstraped by the naming scheme to a path

from typing import List, Any, Dict, Optional, Iterator, TypeVar
from pydantic.v1 import Field
from openad_service_utils import SimpleGenerator
from time import sleep
import random

NO_MODEL = True  # if you are simply providing an api to generate a data set then use false , otherwide True


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
    algorithm_name: str = "MyGeneratorAlgorithm"
    algorithm_application: str = "MySimpleGenerator"
    algorithm_version: str = "v0"

    # define model parameters as fields for the api
    # batch_size: int = Field(description="Prediction batch size", default=128)
    # temperature: float = Field(description="Temperature", default=0.7)
    lchain: list = Field(description="L chain sequence", default=None)
    hchain: list = Field(description="H chain sequence", default=None)

    def setup(self):
        print(">> model filepath: ", self.get_model_location())  # load model
        # self.model_path = self.get_model_location()
        # self.model = MyModel(self.model_path)
        return

    # Override target description in this case we put we make the target a list
    def get_target_description(self) -> Optional[Dict[str, str]]:
        """Get description of the target for generation.
        if not included it will default to a object which is typically a dictionary enclosed in double quotes"""
        return {
            "title": "List of Antigen",
            "type": "list",
            "description": "List of Antigen Sequences to be matched with l-chain and Chain sequences",
        }

    def predict(self, targets: List) -> List[Any]:
        """Implement the generation logic for the new model
        Returns:
            List[Any]: return your predictions
        """

        print("------------------------------------sampling")
        print(targets)
        # Implement the generation logic for the model, This is cancelled out as Example is using NO_MODEL=True
        # self.model.net(self.temperature)
        results = []
        for target in targets:
            for lchain in self.lchain:
                for hchain in self.hchain:
                    results.append(
                        {"lchain": lchain, "hchain": hchain, "antigen": target, "Score": random.uniform(0.01, 1)}
                    )

        return results
