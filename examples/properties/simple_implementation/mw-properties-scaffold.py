###  Model wrapper scaffold for property prediction models
###  -----------------------------------------------------
###  https://github.com/acceleratedscience/openad_service_utils

###  Checklist:
###  ----------
###  [ ] Copy this file and rename it app.py (or alternative name)
###  [ ] Rename the MySimplePredictor class as desired, then:
###      [ ] - Add docstring description
###      [ ] - Configure registry parameters
###      [ ] - Define model parameters in [ZONE B]
###  [ ] Store your model checkpoints and files at the path compiled by self.get_model_location() – see setup()
###  [ ] Set NO_MODEL to True if needed (see comments below)
###  [ ] Insert model imports in [ZONE A]
###  [ ] Insert model instantiation code in [ZONE C]
###  [ ] Insert model execution code in [ZONE D]
###  [ ] Remove or replace all ### comments

###  Testing:
###  --------
###  - Run `python app.py`
###  - See API docs at http://localhost:8080/docs

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
    """
    <model implementation description>
    """  ### <-- Update

    # Registry parameters to fetch model from S3
    # - - -
    # S3 path: domain / algorithm_name / algorithm_application / algorithm_version
    # Run self.get_model_location() to see the compiled path
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "myproperty"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"

    # User-provided parameters for API / model inference
    ### -----------------------------------------
    ### ZONE B: DEFINE MODEL PARAMETERS HERE
    ### - - - - - - - - - - - - - - - - - - - - -
    ### Examples:
    ###     property_type: PredictorTypes = PredictorTypes.MOLECULE
    ###     available_properties: List[PropertyInfo] = [
    ###         PropertyInfo(name="BACE", description=""),
    ###         PropertyInfo(name="ESOL", description=""),
    ###     ]
    ###     hchain_seq: List = Field(
    ###         default=[],
    ###         description="Amino acid sequence of the antibody heavy chain",
    ###     )
    ###     batch_size: int = Field(description="Prediction batch size", default=128)
    ###     workers: int = Field(description="Number of data loading workers", default=8)
    ###     device: str = Field(description="Device to be used for inference", default="cpu")
    ### -----------------------------------------

    def setup(self):
        ### -----------------------------------------
        ### ZONE C: INSERT MODEL INSTANTIATION HERE
        ### - - - - - - - - - - - - - - - - - - - - -
        ### Example:
        ###   self.model_path = self.get_model_location()
        ###   self.model = MyModel(self.model_path)
        ### -----------------------------------------

        print(">> Model filepath: ", self.get_model_location())

        # setup your model
        self.model = None
        self.tokenizer = []
        print(">> model filepath: ", self.get_model_location())
        # -----------------------User Code goes in here------------------------
        self.model_path = os.path.join(
            self.get_model_location(), "model.ckpt"
        )  # load model

    def predict(self, sample: Any):
        """run predictions on your model"""
        # -----------------------User Code goes in here------------------------
        if not self.model:
            self.model = ClassificationModel(
                model=self.algorithm_application,
                model_path=self.model_path,
                tokenizer=self.tokenizer,
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
