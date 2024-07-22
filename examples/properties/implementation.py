import os
from typing import List, Union
from pydantic.v1 import Field
from openad_service_utils.implementation.properties.simple import SimplePredictor, PredictorTypes
from openad_service_utils.common.properties.core import (
    DomainSubmodule,
)


class ClassificationModel:
    """Does nothing. example for a torch model"""
    def __init__(self, model_path, tokenizer) -> None:
        pass
    def to(*args, **kwargs):
        pass
    def eval(*args, **kwargs):
        pass


class MySimplePredictor(SimplePredictor):
    """Class for all Molformer classification algorithms."""
    # necessary params
    algorithm_application: str = "classification"
    algorithm_version: str = "v0"
    algorithm_name: str = "mypredictor"
    domain: DomainSubmodule = DomainSubmodule("molecules")
    property_type = PredictorTypes.MOLECULE
    # user proviced params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")
    # add more params or whatever you want a user to know to change about your model

    def get_model(self, resources_path: str):
        """Instantiate the actual model.

        Args:
            resources_path: local path to model files.

        Returns:
            Predictor: the model.
        """
        # setup your model
        model_path = os.path.join(resources_path, "model.ckpt")
        tokenizer = []
        model = ClassificationModel(model_path=model_path, tokenizer=tokenizer)
        model.to(self.device)
        model.eval()

        # Wrapper to get the predictions
        def informative_model(samples: Union[str, List[str]]) -> List[float]:
            """
            run predictions on your model. For example::
            
                # load dataset or whatever modules you need
                with torch.no_grad():
                    # run predictions
                    predictions = []
                return preds
            """
            return [1]

        return informative_model
