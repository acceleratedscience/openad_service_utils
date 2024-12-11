"""
                NESTED PROPERTY EXAMPLE
The following is an example of how you can nest multiple property inferences under the same simple class and register them for use
The key Difference is rather than defining the SimplePredictorParamters in the Simple Predictor Class we abstracte it as Predictor Class
and enable the setting then passing of the parameters to the Simple Predictor class.

the benefits of this approach is the checkpoints live in separate library paths the downside is that the properties are not generated as
as part of the same command call or request.
"""

import os
from typing import List, Union, Dict, Any
from pydantic.v1 import Field
from openad_service_utils import (
    SimplePredictor,
    SimplePredictorMultiAlgorithm,
    PredictorTypes,
    DomainSubmodule,
    PropertyInfo,
)
from openad_service_utils import start_server

# Example Classifier  / Model Import
# -----------------------USER MODEL LIBRARY-----------------------------------
from property_classifier_example import ClassificationModel

#         USER SETTINGS SECTION
#  import from the nested_parameters.py  library individual Parameters or Paramater sets you wish to use
from nested_parameters import NestedParameters1, NestedParameters2, NESTED_DATA_SETS, get_property_list

# GLOBAL VARIABLES
# API vs Model Call
# Here if you are calling an API  or another Service Set this to True
# Set it to False if you are Calling a Physical Model This setting Will Skip the Model download Process


class MySimplePredictor(SimplePredictor):
    """Class for your Predictor based on Single Predictor to support multiple"""

    """ The following Properties are important they define your bucket path if you are using a model
    in the property generation. the path on disk or in your bucket would be as follows

    domain/algrithm_name/algorithm_application/algorithm_version/
    e.g as below
    /molecules/myproperty/MySimplePredictor/v0

    Note: the algorithm application name and down on first call of the predictor wil lcheck for existance locally
     of the model checkpoint and its entire directory dtruction under the algorithm application name.
    """
    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "myproperty"
    algorithm_application: str = "MySimplePredictor"
    algorithm_version: str = "v0"

    # defines the type of predicTor (CRYSTAL/PROTEIN/MOLECULE)
    property_type: PredictorTypes = PredictorTypes.MOLECULE

    # In the below you can define the valid properties
    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="BACE", description=""),
        PropertyInfo(name="ESOL", description=""),
    ]
    # Note: in this example all of the above parameters get over written on registering of class
    # At registeration you have the option

    # User provided params for api / model inference
    # If not re-speficied in the in the registration process in the case New Parameters are passed the metadata will not be passed bach
    # with service definition to the openad toolkit but will be available to the application

    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")

    def setup(self):
        # setup your model
        print("Setting up model on >> model filepath: ", self.get_model_location())
        self.model_path = self.get_model_location()  # load model
        # ---------------------------------------------------------------------------
        self.tokenizer = []
        self.model = None
        # ---------------------------------------------------------------------------

    def predict(self, sample: Any):
        """run predictions on your model"""

        ## ------------------------- USER LOGIC HERE -------------------------------------------
        if not self.model:
            self.model = ClassificationModel(
                model=self.algorithm_application, model_path=self.model_path, tokenizer=self.tokenizer
            )
            self.model.to(self.device)
        result = self.model.eval(self.get_selected_property())
        # -----------------------------------------------------------------------------------------
        return result


class MySimplePredictorCombo(SimplePredictorMultiAlgorithm):
    """Class for your Predictor based on Combo Predictor to support multiple"""

    """ The following Properties are important they define your bucket path if you are using a model
    in the property generation. the path on disk or in your bucket would be as follows

    domain/algrithm_name/algorithm_application/algorithm_version/
    e.g as below
    /molecules/myproperty/MySimplePredictor/v0

    Note: the algorithm application name and down on first call of the predictor wil lcheck for existance locally
     of the model checkpoint and its entire directory dtruction under the algorithm application name.
    """

    domain: DomainSubmodule = DomainSubmodule("molecules")
    algorithm_name: str = "myproperty"
    algorithm_application: str = "MySimplePredictorCombo"
    algorithm_version: str = "v0"
    property_type: PredictorTypes = PredictorTypes.MOLECULE
    # OPTIONAL (available_properties). Use only if your class implements many models the user can choose from.
    available_properties: List[PropertyInfo] = [
        PropertyInfo(name="BACE", description=""),
        PropertyInfo(name="ESOL", description=""),
    ]

    # Note: in this example all of the above parameters get over written on registering of class
    # At registeration you have the option
    # ------------------------- USER VARIABLES NOT TO BE EXPOSED TO CLIENT HERE -------------------------------------------
    # User provided params for api / model inference
    # If not re-speficied in the in the registration process in the case New Parameters are passed the metadata will not be passed bach
    # with service definition to the openad toolkit but will be available to the application

    # user proviced params for api / model inference
    batch_size: int = Field(description="Prediction batch size", default=128)
    workers: int = Field(description="Number of data loading workers", default=8)
    device: str = Field(description="Device to be used for inference", default="cpu")

    def setup(self):
        """function that automatically gets called on first request to setup each models instance"""
        self.models = {}  # a dictionary of models to be registered
        # setup your model
        self.model_path = os.path.join(self.get_model_location(), "/*.pt")  # load model
        tokenizer = []
        for model in self.available_properties:
            if not self.models.get(model["name"]):
                # ----------------------------- User Classifier --------------
                # Note you may not want to load the model here rather when first inferencing for efficiency
                self.models[model["name"]] = ClassificationModel(
                    model["name"],
                    model_path=self.model_path.replace(f"/{self.algorithm_application}/", f'/{model["name"]}/'),
                    tokenizer=tokenizer,
                )
                print(f"Setting up model {model['name']} on >> model filepath: {self.model_path}")

    # def __init__(self, parameters):
    #    parameters.algorithm_application = parameters.selected_property
    #    super().__init__(parameters)

    def predict(self, sample: Any) -> str | float | int | list | dict:
        """run predictions on your model"""
        ## ------------------------- USER LOGIC HERE -------------------------------------------
        selected_property = self.get_selected_property()  #
        self.models[selected_property].to(self.device)
        result = self.models[selected_property].eval()

        ## -------------------------------------------------------------------------------------

        return result


# register a multiple properties that sit within the same Application and directory structure
props = NestedParameters1()
props.set_parameters(
    algorithm_name="mammal",
    algorithm_application="dti",
    available_properties=[PropertyInfo(name="dti", description="")],
)
MySimplePredictor.register(props, no_model=False)

# register many properties form multiple lists
for key, value in NESTED_DATA_SETS.items():
    props = NestedParameters2()
    props.set_parameters(
        algorithm_name="smi_ted", algorithm_application=key, available_properties=get_property_list(value)
    )
    MySimplePredictorCombo.register(props, no_model=False)  #


# start the service running on port 8080
if __name__ == "__main__":
    # start the server
    start_server(port=8080)
