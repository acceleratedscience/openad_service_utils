import logging
from typing import Optional, ClassVar
from abc import ABC, abstractmethod
from pydantic.v1.dataclasses import dataclass

from pydantic.v1 import Field

from openad_service_utils.common.algorithms.core import (
    ConfigurablePropertyAlgorithmConfiguration,
    PredictorAlgorithm
)

from openad_service_utils.common.properties.core import S3Parameters, DomainSubmodule
from openad_service_utils.common.properties.property_factory import PropertyFactory, PredictorTypes


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
        logger.info("[I] Downloading model: ", configuration.get_application_prefix())
        super().__init__(configuration=configuration)

    @classmethod
    def register(cls, parameters: Optional[PredictorParameters] = None) -> None:
        if not parameters:
            # parameters defined in class
            class_fields = {k: v for k, v in cls.__dict__.items() if not callable(v) and not k.startswith('__')}
            class_fields.pop("_abc_impl", "")
        else:
            class_fields = {k: v for k, v in vars(parameters).items() if not callable(v) and not k.startswith('__')}
        model_params = type(cls.__name__+"Parameters", (S3Parameters, ), class_fields)
        print(f"[i] registering simple predictor: {'/'.join([class_fields.get('domain'), class_fields.get('algorithm_name'), cls.__name__, class_fields.get('algorithm_version')])}\n")
        PropertyFactory.add_predictor(name=cls.__name__, property_type=class_fields.get("property_type"), predictor=(cls, model_params))
