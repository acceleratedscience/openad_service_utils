import os
from typing import List, Union, Dict, Any
from openad_service_utils import start_server
from pydantic.v1 import Field
from openad_service_utils import (
    SimplePredictor,
    PredictorTypes,
    DomainSubmodule,
    PropertyInfo,
)

# -----------------------USER MODEL LIBRARY-----------------------------------
from property_classifier_example import ClassificationModel


class MySimplePredictor(SimplePredictor):
    """Class for all Molformer classification algorithms."""

    # s3 path: domain / algorithm_name / algorithm_application / algorithm_version
    # necessary params
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "smi_ted"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    # OPTIONAL (available_properties). Use only if your class implements many models the user can choose from.
    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="property1", description=""),
        PropertyInfo(name="property2", description=""),
    ]
    # user proviced params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")

    def setup(self):
        # setup your model
        self.model = None
        self.tokenizer = []
        print(">> model filepath: ", self.get_model_location())
        # -----------------------User Code goes in here------------------------
        self.model_path = os.path.join(self.get_model_location(), "model.ckpt")  # load model

    def predict(self, sample: Any):
        """run predictions on your model"""
        # -----------------------User Code goes in here------------------------
        if not self.model:
            self.model = ClassificationModel(
                model=self.algorithm_application, model_path=self.model_path, tokenizer=self.tokenizer
            )
            self.model.to(self.device)

        result = self.model.eval()
        # --------------------------------------------------------------------------
        return result


# register the function in global scope
MySimplePredictor.register(no_model=True)

if __name__ == "__main__":
    # start the server
    start_server(port=8080)
