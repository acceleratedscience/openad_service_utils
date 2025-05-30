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
from openad_service_utils.api import job_manager
from time import sleep

# -----------------------USER MODEL LIBRARY-----------------------------------
from property_classifier_example import ClassificationModel


class MySimplePredictor(SimplePredictor):
    """Class for all Molformer classification algorithms."""

    # s3 path: domain / algorithm_name / algorithm_application / algorithm_version
    # necessary params
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "myproperty"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="BACE", description=""),
        PropertyInfo(name="ESOL", description=""),
    ]
    hchain_seq: List = Field(
        default=[],
        description="Amino acid sequence of the antibody heavy chain",
    )
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
        print("sleeping------------------------------")
        sleep(5)
        print("returning result")
        # --------------------------------------------------------------------------
        return result


# register the function in global scope
MySimplePredictor.register(no_model=True)
import asyncio

if __name__ == "__main__":
    # start the server
    start_server(port=8080)
