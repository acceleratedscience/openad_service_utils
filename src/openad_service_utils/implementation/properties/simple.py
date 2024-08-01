import logging
from abc import ABC, abstractmethod
from typing import ClassVar, Optional

from pydantic.v1 import Field
from pydantic.v1.dataclasses import dataclass

from openad_service_utils.common.algorithms.core import (
    ConfigurablePropertyAlgorithmConfiguration, Predictor, PredictorAlgorithm)
from openad_service_utils.common.properties.core import (DomainSubmodule,
                                                         S3Parameters)
from openad_service_utils.common.properties.property_factory import (
    PredictorTypes, PropertyFactory)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass
class PredictorParameters:
    """
    Helper class for adding parameters to your model outside of class::SimplePredictor

    example::

        class MyParams(PredictorParameters):
            temperature: int = Field(description="", default=7)
        
        class MyPredictor(SimplePredictor):
            pass
        
        MyPredictor.register(MyParams)
    """
    domain: DomainSubmodule = Field(
        ..., example="molecules", description="Submodule of gt4sd.properties"
    )
    algorithm_name: str = Field(..., example="MCA", description="Name of the algorithm")
    algorithm_version: str = Field(
        ..., example="v0", description="Version of the algorithm"
    )
    algorithm_application: str = Field(..., example="Tox21")


class SimplePredictor(PredictorAlgorithm, ABC):
    """Interface for automated prediction via an :class:`ConfigurablePropertyAlgorithmConfiguration`.

    Do not implement __init__()
    
    """
    property_type: ClassVar[PredictorTypes]

    def __init__(self, parameters: S3Parameters):
        # revert class level parameters from pydantic Fields to class attributes
        # this lets you access them when instantiated e.g. self.device
        for key, value in vars(parameters).items():
            setattr(self, key, value)
        configuration = ConfigurablePropertyAlgorithmConfiguration(
            algorithm_type=parameters.algorithm_type,
            domain=parameters.domain,
            algorithm_name=parameters.algorithm_name,
            algorithm_application=parameters.algorithm_application,
            algorithm_version=parameters.algorithm_version,
        )
        # The parent constructor calls `self.get_model`.
        print(f"[i] downloading model: {parameters.algorithm_name}/{parameters.algorithm_version}", )
        # logger.info("[I] Downloading model: ", configuration.get_application_prefix())
        super().__init__(configuration=configuration)
    
    def get_model_location(self):
        """get path to model"""
        return self.local_artifacts
    
    @abstractmethod
    def setup_model(self):
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
        model_params = type(cls.__name__+"Parameters", (S3Parameters, ), class_fields)
        if class_fields.get("algorithm_application"):
            logger.debug(f"updating application name from '{cls.__name__}' to '{class_fields.get('algorithm_application')}'")
            cls.__name__ = class_fields.get("algorithm_application")
        print(f"[i] registering simple predictor: {'/'.join([class_fields.get('domain'), class_fields.get('algorithm_name'), cls.__name__, class_fields.get('algorithm_version')])}\n")
        PropertyFactory.add_predictor(name=cls.__name__, property_type=class_fields.get("property_type"), predictor=(cls, model_params))
