import os
from typing import List, Union, Dict, Any
from openad_service_utils.common.algorithms.core import Predictor
from pydantic.v1 import Field
from openad_service_utils import (
    SimplePredictor,
    PredictorTypes,
    DomainSubmodule,
    PropertyInfo,
)
from openad_service_utils.common.algorithms.core import AlgorithmConfiguration
from property_classifier_example import ClassificationModel

# use No Model if simply calling an API or wrapper to another service
NO_MODEL = True  # ATTENTION SET to TRUE ONLY for Example ...


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
    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="property1", description=""),
        PropertyInfo(name="property2", description=""),
    ]

    # user proviced params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")
    model = None

    def setup(self):
        # setup your model
        print(">> model filepath: ", self.get_model_location())
        model_path = os.path.join(self.get_model_location(), "model.ckpt")  # load model
        tokenizer = []
        if not self.model:
            self.model = ClassificationModel(
                model=self.algorithm_application, model_path=model_path, tokenizer=tokenizer
            )
            self.model.to(self.device)

    def get_predictor(self, configuration: AlgorithmConfiguration):
        """overwrite existing function to download model only once"""
        global NO_MODEL
        if NO_MODEL is False:
            super().get_predictor(self)
        else:
            print("no predictor")

    def predict(self, sample: Any):
        """run predictions on your model"""
        result = self.model.eval()
        return result
