import logging
import os
import pprint
from abc import ABC, abstractmethod
from typing import ClassVar, List, Optional, TypedDict, Dict, Any

from pydantic.v1 import BaseModel, Field

from openad_service_utils.common.algorithms.core import (
    AlgorithmConfiguration, ConfigurablePropertyAlgorithmConfiguration,
    Predictor, PredictorAlgorithm)
from openad_service_utils.common.configuration import get_cached_algorithm_path
from openad_service_utils.common.properties.core import (DomainSubmodule,
                                                         S3Parameters)
from openad_service_utils.common.properties.property_factory import (
    PredictorTypes, PropertyFactory)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def get_properties_model_path(domain: str, algorithm_name: str, algorithm_application: str, algorithm_version: str) -> str:
    """generate the model path location"""
    prefix = os.path.join(
        domain,
        algorithm_name,
        algorithm_application,
        algorithm_version,
        )
    return get_cached_algorithm_path(prefix, module="properties")


class PropertyInfo(TypedDict):
    name: str
    description: str


class BasePredictorParameters:
    # TODO: change all this into 1 base_model_path or have user implement their style of downloading e.g. remove configuration dependency
    algorithm_type: str = "prediction"
    domain: DomainSubmodule = Field(
        ..., example="molecules", description="Submodule of gt4sd.properties"
    )
    algorithm_name: str = Field(..., example="MCA", description="Name of the algorithm")
    algorithm_version: str = Field(
        ..., example="v0", description="Version of the algorithm"
    )
    algorithm_application: str = Field(..., example="Tox21")


class PredictorParameters(BaseModel):
    """
    Helper class for adding parameters to your model outside of class::SimplePredictor

    example::

        class MyParams(PredictorParameters):
            temperature: int = Field(description="", default=7)
        
        class MyPredictor(SimplePredictor):
            pass
        
        MyPredictor.register(MyParams)
    """
    algorithm_type: str = "prediction"
    domain: DomainSubmodule = Field(
        ..., example="molecules", description="Submodule of gt4sd.properties"
    )
    algorithm_name: str = Field(..., example="MCA", description="Name of the algorithm")
    algorithm_version: str = Field(
        ..., example="v0", description="Version of the algorithm"
    )
    algorithm_application: str = Field(..., example="Tox21")
    # this is used to select a var::PropertyInfo.name available_properties. User selected property from api.
    # this is not harcoded in the class, but is added to the class when registering the predictor
    selected_property: str = ""


class SimplePredictor(PredictorAlgorithm, BasePredictorParameters):
    """Class to create an api for a predictor model.

    Do not implement __init__() or instatiate this class.

    1. Setup your predictor. Ease child implementation. For example::

        from openad_service_utils import SimplePredictor

        class YourApplicationName(SimplePredictor):
            # necessary s3 paramters
            domain: str = "molecules"
            algorithm_name: str = "MyAlgorithmName"
            algorithm_application: str = "MyApplicationName"
            algorithm_version: str = "v0"
            # necessary api types
            property_type: PredictorTypes
            available_properties: List[PropertyInfo] = []
            # your custom api paramters
            some_parameter1: float = 1.61
            some_parameter2: float = 1.61

        def setup(self) -> List[Any]:
            # load model
        
        def predict(sample: Any):
            # setup model prediction
    
    2. Register the Predictor::

        YourApplicationName.register()
    
    """
    # algorithm_type: ClassVar[str] = ""  # hardcoded because we dont care about it. does nothing.
    property_type: PredictorTypes
    available_properties: Optional[List[PropertyInfo]] = []

    __artifacts_downloaded__: bool = False

    def __init__(self, parameters: PredictorParameters):
        """Do not implement or instatiate"""
        # revert class level parameters from pydantic Fields to class attributes
        # this lets you access them when instantiated e.g. self.device
        for key, value in vars(parameters).items():
            setattr(self, key, value)
        # set up the configuration
        configuration = ConfigurablePropertyAlgorithmConfiguration(
            algorithm_type=parameters.algorithm_type,
            domain=parameters.domain,
            algorithm_name=parameters.algorithm_name,
            algorithm_application=parameters.algorithm_application,
            algorithm_version=parameters.algorithm_version,
        )
        super().__init__(configuration=configuration)
        # run the user model setup
        self.setup()
    
    def get_model_location(self):
        """get path to model"""
        prefix = os.path.join(
            self.configuration.get_application_prefix(),
            self.configuration.algorithm_version,
        )
        return get_cached_algorithm_path(prefix, module="properties")

    def __download_model(self):
        """download model from s3"""
        if not self.__artifacts_downloaded__:
            logger.info(f"[I] Downloading model: {self.configuration.algorithm_application}/{self.configuration.algorithm_version}")
            if self.configuration.ensure_artifacts():
                SimplePredictor.__artifacts_downloaded__ = True
                logger.info(f"[I] model downloaded")
            else:
                logger.error("[E] could not download model")
        else:
            logger.info(f"[I] model already downloaded")
    
    def get_predictor(self, configuration: AlgorithmConfiguration):
        """overwrite existing function to download model only once"""
        # download model
        self.__download_model()
        # get prediction function
        model: Predictor = self.get_model(self.get_model_location())
        return model
    
    def get_selected_property(self) -> str:
        return self.selected_property
    
    def get_model(self, resources_path: str):
        """do not use. do not overwrite!"""
        # implement abstracted class
        return self.predict
    
    @abstractmethod
    def setup(self):
        """Set up the model."""
        raise NotImplementedError("Not implemented in baseclass.")
    
    @abstractmethod
    def predict(self, sample: Any):
        """Run predictions and return results."""
        raise NotImplementedError("Not implemented in baseclass.")

    @classmethod
    def register(cls, parameters: Optional[PredictorParameters] = None) -> None:
        if not parameters:
            # parameters defined in class
            class_fields = {k: v for k, v in cls.__dict__.items() if not callable(v) and not k.startswith('__')}
            class_fields.pop("_abc_impl", "")
        else:
            class_fields = {k: v for k, v in vars(parameters).items() if not callable(v) and not k.startswith('__')}
        # check if required fields are set
        required = ["algorithm_name", "domain", "algorithm_version", "algorithm_application", "property_type"]
        for field in required:
            if field not in class_fields:
                raise TypeError(f"Can't instantiate class ({cls.__name__}) without '{field}' class variable")
        # update class name to be `algorithm_application`
        cls.__name__ = class_fields.get("algorithm_application")
        # setup s3 class params
        model_param_class: PredictorParameters = type(cls.__name__+"Parameters", (PredictorParameters, ), class_fields)
        if class_fields.get("available_properties"):
            if not isinstance(class_fields.get("available_properties"), list):
                raise ValueError("available_properties must be of List[PropertyInfo]")
            # set all property types in PropertyFactory. available_properties -> valid_types
            for predictor_name in class_fields.get("available_properties"):
                if isinstance(predictor_name, dict):
                    predictor_name = predictor_name.get("name")
                PropertyFactory.add_predictor(name=predictor_name, property_type=class_fields.get("property_type"), predictor=(cls, model_param_class))
        else:
            # set class name as property type in PropertyFactory
            PropertyFactory.add_predictor(name=cls.__name__, property_type=class_fields.get("property_type"), predictor=(cls, model_param_class))
        model_location = get_properties_model_path(class_fields.get("domain"), class_fields.get("algorithm_name"), cls.__name__, class_fields.get("algorithm_version"))
        print(f"[i] registering predictor model: {model_location}")
        # print(cls(model_param_class(**model_param_class().dict())).get_model_location())
