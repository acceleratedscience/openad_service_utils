import os
from typing import List, Union
from pydantic.v1 import Field
from openad_service_utils import SimplePredictor, PredictorTypes, DomainSubmodule


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
    # s3 path: domain / algorithm_name / algorithm_application / algorithm_version
    # necessary params
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "mypredictor"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE

    # user proviced params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")

    def setup_model(self):
        """Instantiate the actual model.

        Args:
            resources_path: local path to model files.

        Returns:
            Predictor: the model.
        """
        # setup your model
        print(">> model filepath: ", self.get_model_location())
        model_path = os.path.join( self.get_model_location(), "model.ckpt")  # load model
        tokenizer = []
        model = ClassificationModel(model_path=model_path, tokenizer=tokenizer)
        model.to(self.device)
        model.eval()
        # callable function to get the predictions
        def informative_model(samples: Union[str, List[str]]) -> List[float]:
            """
            run predictions on your model. For example::
            
                # load dataset or whatever modules you need
                with torch.no_grad():
                    # run predictions
                    predictions = []
                return preds
            """
            return [1,0,1]
        # return callable
        return informative_model
