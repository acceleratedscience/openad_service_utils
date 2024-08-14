import logging
import os
from abc import ABC, abstractmethod
from typing import ClassVar, List, Optional, TypedDict, Dict

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


class PropertyInfo(TypedDict):
    name: str
    description: str



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
    selected_property: str = ""


class SimplePredictor(PredictorAlgorithm, ABC):
    """Interface for automated prediction via an :class:`ConfigurablePropertyAlgorithmConfiguration`.

    Do not implement __init__()

    The signature of this class constructor (given by the instance attributes) is used
    for the REST API and needs to be serializable.

    1. Setup your predictor. Ease child implementation. For example::

        from openad_service_utils import SimplePredictor

        class YourApplicationName(SimplePredictor):
            domain: str = "molecules"
            algorithm_name = "MyGeneratorAlgorithm"
            algorithm_application: str = "MyApplication"
            algorithm_version: str = "v0"

            actual_parameter1: float = 1.61
            actual_parameter2: float = 1.61
            ...

            # no __init__ definition required
        def setup_model(self) -> List[Any]:
            # implementation goes here
            def informative_model(samples):
                predictions = [1,2,3]
                return predictions
            
            return informative_model
    
    2. Register the Predictor::

        YourApplicationName.register()
    
    """
    algorithm_type: ClassVar[str] = ""  # hardcoded because we dont care about it. does nothing.
    property_type: ClassVar[PredictorTypes]
    available_properties: ClassVar[List[PropertyInfo]] = []
    # available_properties: ClassVar[List] = []

    __artifacts_downloaded__: bool = False

    def __init__(self, parameters: S3Parameters):
        # revert class level parameters from pydantic Fields to class attributes
        # this lets you access them when instantiated e.g. self.device
        for key, value in vars(parameters).items():
            # print("setting ", key)
            setattr(self, key, value)
        configuration = ConfigurablePropertyAlgorithmConfiguration(
            algorithm_type=parameters.algorithm_type,
            domain=parameters.domain,
            algorithm_name=parameters.algorithm_name,
            algorithm_application=parameters.algorithm_application,
            algorithm_version=parameters.algorithm_version,
        )
        super().__init__(configuration=configuration)
    
    def get_model_location(self):
        """get path to model"""
        prefix = os.path.join(
            self.configuration.get_application_prefix(),
            self.configuration.algorithm_version,
        )
        return get_cached_algorithm_path(prefix, module="properties")
    
    def get_predictor(self, configuration: AlgorithmConfiguration):
        """overwrite existing function to download model only once"""
        logger.info("ensure artifacts for the application are present.")
        if not self.__artifacts_downloaded__:
            print(f"[I] Downloading model: {configuration.algorithm_application}/{configuration.algorithm_version}")
            if configuration.ensure_artifacts():
                SimplePredictor.__artifacts_downloaded__ = True
            else:
                print("[E] could not download model")
        else:
            logger.info(f"[I] model already downloaded")
        model: Predictor = self.get_model(self.get_model_location())
        return model
    
    def get_selected_property(self) -> str:
        return self.selected_property
    
    @abstractmethod
    def setup_model(self) -> Predictor:
        """
        This is the major method to implement in child classes, it is called
        at instantiation of the SimplePredictor and must return a callable:

        Returns:
            Predictor (callable)
        """
        raise NotImplementedError("Not implemented in baseclass.")

    def get_model(self, resources_path: str):
        """do not implement. implement setup_model instead."""
        return self.setup_model()

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
        model_params = type(cls.__name__+"Parameters", (PredictorParameters, ), class_fields)
        print(f"[i] registering simple predictor: {'/'.join([class_fields.get('domain'), class_fields.get('algorithm_name'), cls.__name__, class_fields.get('algorithm_version')])}\n")
        if class_fields.get("available_properties"):
            # set all property types in PropertyFactory
            for predictor_name in class_fields.get("available_properties"):
                if isinstance(predictor_name, dict):
                    predictor_name = predictor_name.get("name")
                PropertyFactory.add_predictor(name=predictor_name, property_type=class_fields.get("property_type"), predictor=(cls, model_params))
        else:
            # set class name as property type in PropertyFactory
            PropertyFactory.add_predictor(name=cls.__name__, property_type=class_fields.get("property_type"), predictor=(cls, model_params))
