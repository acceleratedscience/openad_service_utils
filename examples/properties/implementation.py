import os
from typing import List, Any
from pydantic import Field
from openad_service_utils import (
    SimplePredictor, 
    PredictorTypes, 
    DomainSubmodule, 
    PropertyInfo
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
    # s3 path: domain / algorithm_name / algorithm_application / algorithm_version
    # necessary params
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "mypredictor"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    # OPTIONAL (available_properties). Use only if your class implements many models the user can choose from.
    available_properties: List[PropertyInfo] = [PropertyInfo(name="property1", description=""), PropertyInfo(name="property2", description="")]

    # user proviced params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")

    def setup(self):
        # setup your model
        print(">> model filepath: ", self.get_model_location())
        model_path = os.path.join( self.get_model_location(), "model.ckpt")  # load model
        tokenizer = []
        model = ClassificationModel(model_path=model_path, tokenizer=tokenizer)
        model.to(self.device)
        model.eval()
    
    def predict(self, sample: Any):
        """run predictions on your model"""
        selected_property = self.get_selected_property()
        print(">> SELECTED PROPERTY: ", selected_property)
        return [1,0,1]
