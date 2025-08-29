import logging
import os
from abc import ABC, abstractmethod
from typing import ClassVar, List, Optional, TypedDict, Dict, Any, Union, Type, cast

from pydantic.v1 import BaseModel, Field

from openad_service_utils.common.algorithms.core import (
    AlgorithmConfiguration,
    ConfigurablePropertyAlgorithmConfiguration,
    Predictor,
    PredictorAlgorithm,
)
from openad_service_utils.common.configuration import get_cached_algorithm_path
from openad_service_utils.common.properties.core import DomainSubmodule, S3Parameters, Mesh, PropertyPredictorParameters
from openad_service_utils.common.properties.property_factory import (
    PredictorTypes,
    PropertyFactory,
)
from openad_service_utils.utils.logging_config import setup_logging

# Set up logging configuration
setup_logging()

# Create a logger
logger = logging.getLogger(__name__)


def get_properties_model_path(
    domain: str, algorithm_name: str, algorithm_application: str, algorithm_version: str
) -> str:
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
    domain: DomainSubmodule = Field(..., example="molecules", description="Submodule of gt4sd.properties")
    algorithm_name: str = Field(..., example="MCA", description="Name of the algorithm")
    algorithm_version: str = Field(..., example="v0", description="Version of the algorithm")
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
    domain: DomainSubmodule = Field(..., example="molecules", description="Submodule of gt4sd.properties")
    algorithm_name: str = Field(..., example="MCA", description="Name of the algorithm")
    algorithm_version: str = Field(..., example="v0", description="Version of the algorithm")
    algorithm_application: str = Field(..., example="Tox21")
    # this is used to select a var::PropertyInfo.name available_properties. User selected property from api.
    # this is not harcoded in the class, but is added to the class when registering the predictor
    selected_property: str = ""
    subjects: Optional[List[Union[str, Mesh, Dict[str, Any]]]] = Field(
        None, description="List of subjects for prediction (e.g., SMILES strings, protein sequences, or Mesh objects)."
    )
    file_keys: Optional[List[str]] = Field(None, description="List of file paths for uploaded subjects.")


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
    selected_property: str = ""
    configuration: Optional[ConfigurablePropertyAlgorithmConfiguration] = None

    __artifacts_downloaded__: bool = False
    __no_model__: bool = False

    def __init__(self, parameters: PredictorParameters):
        """Do not implement or instatiate"""
        # set up the configuration
        self._update_parameters(parameters)
        # run the user model setup
        self.setup()

    def _update_parameters(self, parameters: PredictorParameters):
        """Update model params with user input"""
        # update the parameters
        for key, value in vars(parameters).items():
            setattr(self, key, value)
        # if PredictorParameters variables changed then we need to re-download the model
        # TODO: add tests
        if self.configuration and (
            self.configuration.algorithm_application != parameters.algorithm_application
            or self.configuration.algorithm_version != parameters.algorithm_version
        ):
            self.__artifacts_downloaded__ = False
            logger.info(
                f"Re-downloading model: {self.configuration.algorithm_application}/{self.configuration.algorithm_version}"
            )
        # set up the configuration
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
        if self.configuration is None:
            raise ValueError("Model configuration is not set.")
        prefix = os.path.join(
            self.configuration.get_application_prefix(),
            self.configuration.algorithm_version,
        )
        return get_cached_algorithm_path(prefix, module="properties")

    def __download_model(self):
        """download model from s3"""
        if self.__no_model__:
            logger.info(f"No Model required ")
            return
        if self.configuration is None:
            raise ValueError("Model configuration is not set.")
        if not self.__artifacts_downloaded__:
            logger.info(
                f"Downloading model: {self.configuration.algorithm_application}/{self.configuration.algorithm_version}"
            )
            if self.configuration.ensure_artifacts():
                self.__artifacts_downloaded__ = True
                # logger.info(f"model downloaded")
            else:
                logger.error("could not download model")
        else:
            logger.info(f"model already downloaded")

    def get_predictor(self, configuration: AlgorithmConfiguration) -> Predictor:
        """overwrite existing function to download model only once"""
        # download model
        if self.__no_model__:
            logger.info("No model required, skipping S3 caching.")
            # If no model is required, we still return the predict method,
            # and the user's predict method should handle the no-model case.
            return cast(Predictor, self.predict)
        self.__download_model()
        # get prediction function
        model = self.get_model(self.get_model_location())
        return cast(Predictor, model)

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
    def predict(self, input: Any) -> Union[Dict[str, Any], List[Any], str, int, float, bool, None]:
        """Run predictions and return results in JSON serializable format."""

        raise NotImplementedError("Not implemented in baseclass.")

    @classmethod
    def register(cls, parameters: Optional[PredictorParameters] = None, no_model=False) -> None:
        """**no_model** : defaults to false, so that the model is always retrieved. If on register this is set to true, allows the user to manage loading of checkpoint or
        the ability to run a inference that only uses an API to retrieve a result"""
        if not parameters:
            # parameters defined in class
            class_fields = {k: v for k, v in cls.__dict__.items() if not callable(v) and not k.startswith("__")}
            class_fields.pop("_abc_impl", "")
        else:
            class_fields = {k: v for k, v in vars(parameters).items() if not callable(v) and not k.startswith("__")}
        # check if required fields are set
        required = [
            "algorithm_name",
            "domain",
            "algorithm_version",
            "algorithm_application",
            "property_type",
        ]
        for field in required:
            if field not in class_fields:
                raise TypeError(f"Can't instantiate class ({cls.__name__}) without '{field}' class variable")
        # update class name to be `algorithm_application`
        # cls.__name__ = class_fields.get("algorithm_application") # Removed: __name__ is read-only
        cls.__no_model__ = no_model
        # setup s3 class params
        # Ensure algorithm_application is a string before using it in type name
        app_name = class_fields.get("algorithm_application", cls.__name__)
        if not isinstance(app_name, str):
            app_name = str(app_name)

        # Initialize variables with explicit types and handle potential None from .get()
        domain_val: DomainSubmodule = cast(DomainSubmodule, class_fields.get("domain"))
        if not isinstance(domain_val, DomainSubmodule):
            raise TypeError(f"Domain must be a DomainSubmodule enum, got {type(domain_val)}")
        
        algo_name_val: str = cast(str, class_fields.get("algorithm_name"))
        if not isinstance(algo_name_val, str):
            raise TypeError(f"Algorithm name must be a string, got {type(algo_name_val)}")
        
        algo_version_val: str = cast(str, class_fields.get("algorithm_version"))
        if not isinstance(algo_version_val, str):
            raise TypeError(f"Algorithm version must be a string, got {type(algo_version_val)}")

        model_param_class: Type[PredictorParameters] = type(f"{app_name}Parameters", (PredictorParameters,), class_fields)

        if class_fields.get("available_properties"):
            available_props = class_fields.get("available_properties")
            if not isinstance(available_props, list):
                raise ValueError("available_properties must be of List[PropertyInfo]")
            # set all property types in PropertyFactory. available_properties -> valid_types
            for predictor_info in available_props:
                if isinstance(predictor_info, dict):
                    predictor_name = predictor_info.get("name")
                else:
                    predictor_name = predictor_info # Assuming it's a string if not a dict
                if not isinstance(predictor_name, str):
                    raise TypeError(f"Predictor name must be a string, got {type(predictor_name)}")

                property_type_val = cast(PredictorTypes, class_fields.get("property_type"))
                if not isinstance(property_type_val, PredictorTypes):
                    raise TypeError(f"Property type must be a PredictorTypes enum, got {type(property_type_val)}")

                PropertyFactory.add_predictor(
                    name=predictor_name,
                    property_type=property_type_val,
                    predictor=(cls, cast(Type[PropertyPredictorParameters], model_param_class)),
                )
        else:
            # set class name as property type in PropertyFactory
            property_type_val = cast(PredictorTypes, class_fields.get("property_type"))
            if not isinstance(property_type_val, PredictorTypes):
                raise TypeError(f"Property type must be a PredictorTypes enum, got {type(property_type_val)}")

            PropertyFactory.add_predictor(
                name=cls.__name__,
                property_type=property_type_val,
                predictor=(cls, cast(Type[PropertyPredictorParameters], model_param_class)),
            )

        model_location = get_properties_model_path(
            domain_val,
            algo_name_val,
            app_name, # Use app_name here
            algo_version_val,
        )
        try:
            os.makedirs(model_location, exist_ok=True)
        except Exception:
            logger.error(f"could not create model cache location: {model_location}")
        logger.info(f"registering predictor model: {model_location}")
        # logger.debug(cls(model_param_class(**model_param_class().dict())).get_model_location())


class SimplePredictorMultiAlgorithm(SimplePredictor):

    def get_model_location(self):
        """gets the true path of a property checkpoint"""
        return (
            super().get_model_location().replace(f"/{self.algorithm_application}/", f"/{self.get_selected_property()}/")
        )

    def _update_parameters(self, parameters: PredictorParameters):
        """Update model params with user input"""
        if self.configuration:
            parameters.algorithm_application = self.configuration.algorithm_application
        super()._update_parameters(parameters)

    def get_predictor(self, configuration: AlgorithmConfiguration) -> Predictor:
        """overwrite existing function to download model only once"""
        # download model
        if self.__no_model__:
            logger.info("No model required, skipping download.")
            return cast(Predictor, self.predict) # Return casted predict method
        # .__download_model()
        # get prediction function
        self.__download_model()
        model = self.get_model(self.get_model_location())

        return cast(Predictor, model) # Cast the model to Predictor

    def __init__(self, parameters):
        parameters.algorithm_application = parameters.selected_property
        super().__init__(parameters)

    def __download_model(self):
        """download model from s3"""
        if self.__no_model__:
            logger.info(f"No Model required ")
            return
        if self.configuration is None:
            raise ValueError("Model configuration is not set.")
        if not self.__artifacts_downloaded__:

            logger.info(f"Downloading model: {self.get_selected_property()}/{self.configuration.algorithm_version}")
            if self.configuration.ensure_artifacts():
                self.__artifacts_downloaded__ = True
                # logger.info(f"model downloaded")
            else:
                logger.error("could not download model")
        else:
            logger.info(f"model already downloaded")
