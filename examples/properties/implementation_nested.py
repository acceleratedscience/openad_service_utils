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
from openad_service_utils import SimplePredictor, PredictorTypes, DomainSubmodule, PropertyInfo
from openad_service_utils.common.algorithms.core import AlgorithmConfiguration
from openad_service_utils import start_server

# Example Classifier  / Model Import
# Replace this with your classifiers
from property_classifier_example import ClassificationModel


# use No Model if simply calling an API or wrapper to another service

#         USER SETTINGS SECTION

#  import from the nested_parameters.py  library individual Parameters or Paramater sets you wish to use
from nested_parameters import NestedParameters1, NestedParameters2, NESTED_DATA_SETS, get_property_list

# GLOBAL VARIABLES
""" API vs Model Call 
# Here if you are calling an API  oranother Service Set this to True
# Set it to False if you are Calling a Physical Model
# This setting Will Skip the Model download Process
"""
NO_MODEL = True  # ATTENTION SET to TRUE ONLY for Example using AP...


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
    model = None

    def setup(self):
        # setup your model
        print("Setting up model on >> model filepath: ", self.get_model_location())
        model_path = os.path.join(self.get_model_location(), "model.ckpt")  # load model
        # ---------------------------------------------------------------------------
        tokenizer = []
        if not self.model:
            self.model = ClassificationModel(
                model=self.algorithm_application, model_path=model_path, tokenizer=tokenizer
            )
            self.model.to(self.device)
        # ---------------------------------------------------------------------------

    def get_predictor(self, configuration: AlgorithmConfiguration):
        """overwrite existing function to download model only once"""
        global NO_MODEL
        if NO_MODEL is False:
            super().get_predictor(self)
        else:
            print("no predictor")

    def predict(self, sample: Any):
        """run predictions on your model"""

        ## ------------------------- USER LOGIC HERE -------------------------------------------

        result = self.model.eval()
        # -----------------------------------------------------------------------------------------
        return result


class MySimplePredictorCombo(SimplePredictor):
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
        model_path = os.path.join(self.get_model_location(), "model.ckpt")  # load model
        tokenizer = []
        for model in self.available_properties:
            if not self.models.get(model["name"]):
                self.models[model["name"]] = ClassificationModel(
                    model["name"],
                    model_path=model_path.replace(f"/{self.algorithm_application}/", f'/{model["name"]}/'),
                    tokenizer=tokenizer,
                )
                print(f"Setting up model {model['name']} on >> model filepath: {model_path}")

    def get_predictor(self, configuration: AlgorithmConfiguration):
        """Override of get predictor function so as to avoid trying to load a checkpoint if API only"""
        global NO_MODEL  # import the global model varaible to determine if service has model or API only

        if NO_MODEL is False:
            super().get_predictor(
                self
            )  # pulls checkpoint and if not local goes to load all files in the the algorithm_application directory form S3
        else:
            print("Running in API only model mode with no model")

    def predict(self, sample: Any) -> str | float | int | list | dict:
        """run predictions on your model"""
        ## ------------------------- USER LOGIC HERE -------------------------------------------
        selected_property = self.get_selected_property()  #
        self.models[selected_property].to(self.device)
        result = self.models[selected_property].eval()

        ## -------------------------------------------------------------------------------------

        return result  # str, number,list


# register a single Property
props = NestedParameters1()
props.set_parameters("base_1", available_properties=[PropertyInfo(name="BACE1", description="")])
MySimplePredictor.register(props)

props = NestedParameters1()
props.set_parameters("ESOL1", available_properties=[PropertyInfo(name="ESOL", description="")])
MySimplePredictor.register(props)

# register a multiple properties
props = NestedParameters1()
props.set_parameters(
    "ESOLduoploy",
    available_properties=[PropertyInfo(name="ESOL2", description=""), PropertyInfo(name="ESOL3", description="")],
)
MySimplePredictor.register(props)


# register many properties form multiple lists
for key, value in NESTED_DATA_SETS.items():

    props = NestedParameters2()
    props.set_parameters(
        key,
        available_properties=get_property_list(value),
    )
    MySimplePredictorCombo.register(props)  #


# start the service running on port 8080
if __name__ == "__main__":
    # start the server
    start_server(port=8080)
