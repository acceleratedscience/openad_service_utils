# simple.py
# follows a simpler gt4sd registry pattern
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional, TypeVar, Union

from openad_service_utils import ApplicationsRegistry
from openad_service_utils.common.algorithms.core import (
    AlgorithmConfiguration,
    GeneratorAlgorithm,
    Targeted,
    Untargeted,
)
from openad_service_utils.common.configuration import get_cached_algorithm_path
from openad_service_utils.utils.logging_config import setup_logging

# Set up logging configuration
setup_logging()

# Create a logger
logger = logging.getLogger(__name__)

# leave typing generic for algorithm implementation
S = TypeVar("S")  # used for generated items
T = TypeVar("T")  # used for target of generation
U = TypeVar("U")  # used for additional context (e.g. part of target definition)


def get_properties_model_path(
    algorithm_type: str,
    algorithm_name: str,
    algorithm_application: str,
    algorithm_version: str,
) -> str:
    """generate the model path location"""
    prefix = os.path.join(
        algorithm_type,
        algorithm_name,
        algorithm_application,
        algorithm_version,
    )
    return get_cached_algorithm_path(prefix, module="algorithms")


class SimpleGenerator(AlgorithmConfiguration[S, T], ABC):
    """Class to create an api for a generator algorithm.

    Do not implement __init__() or instatiate this class.

    1. Setup your generator. Ease child implementation. For example::

        from openad_service_utils import SimpleGenerator

        class YourApplicationName(SimpleGenerator):
            # necessary s3 paramters
            algorithm_type: str = "conditional_generation"
            algorithm_name: str = "MyGeneratorAlgorithm"
            algorithm_application: str = "MySimpleGenerator"
            algorithm_version: str = "v0"
            # your custom api paramters
            actual_parameter1: float = 1.61
            actual_parameter2: float = 1.61

        def setup(self) -> List[Any]:
            # load model

        def predict(self) -> List[Any]:
            # setup model prediction

    2. Register the Generator::

        YourApplicationName.register()
    """

    domain: ClassVar[
        str
    ] = "materials"  # hardcoded because we dont care about it. does nothing but need it.

    def get_model_location(self):
        """get path to model"""
        prefix = os.path.join(
            self.get_application_prefix(),
            self.algorithm_version,
        )
        return get_cached_algorithm_path(prefix)

    @classmethod
    def register(cls):
        """Register the configuration with the ApplicationsRegistry and load the model into runtime."""
        required = ["algorithm_name", "algorithm_type"]
        for field in required:
            if field not in cls.__dict__:
                raise TypeError(
                    f"Can't instantiate class ({cls.__name__}) without '{field}' class variable"
                )
        # create during runtime so that user doesnt have to write separate algorithm class
        algorithm = type(cls.algorithm_name, (BaseAlgorithm,), {})
        # update class name to application name
        if cls.algorithm_application:
            logger.debug(
                f"updating application name from '{cls.__name__}' to '{cls.algorithm_application}'"
            )
            cls.__name__ = cls.algorithm_application
        model_location = get_properties_model_path(
            cls.algorithm_type, cls.algorithm_name, cls.__name__, cls.algorithm_version
        )
        logger.info(f"registering generator model: {model_location}")
        try:
            os.makedirs(model_location, exist_ok=True)
        except Exception:
            logger.error(f"could not create model cache location: {model_location}")
        ApplicationsRegistry.register_algorithm_application(algorithm)(cls)

    @abstractmethod
    def setup(self):
        """
        This is the major method to implement in child classes
        """
        raise NotImplementedError("Not implemented in baseclass.")

    @abstractmethod
    def predict(self, samples: list):
        """
        This is the major method to implement in child classes, it is called
        at instantiation of the SimpleGenerator and must return a List[Any]:

        Returns:
            Iterable[Any]
        """
        raise NotImplementedError("Not implemented in baseclass.")

    def generate(self, target: Optional[T] = None) -> List[Any]:
        """do not implement. implement predict instead."""
        if isinstance(target, str):
            # TODO: validate
            target = [target]
        return self.predict(target)


class BaseAlgorithm(GeneratorAlgorithm[S, T]):
    """Interface for automated generation via an :class:`SimpleGenerator`."""

    __artifacts_downloaded__: bool = False

    def __init__(self, configuration: SimpleGenerator, target: Optional[T] = None):
        super().__init__(configuration=configuration, target=target)
        # run the user model setup
        configuration.setup()

    def get_generator(
        self,
        configuration: SimpleGenerator[S, T],
        target: Optional[T],
    ) -> Untargeted:
        # ) -> Union[Untargeted, Targeted[T]]:
        """Set up the detail implementation using the configuration. This Base implementation returns an untargeted generator.

        Note:
            This is the major method to implement in child classes, it is called
            at instantiation of the GeneratorAlgorithm and must return a callable:

            - Either :obj:`Untargeted`: the callable is taking no arguements,
              and target has to be :obj:`None`.
            - Or :obj:`Targeted`: the callable with the target (but not :obj:`None`).

        Args:
            configuration: application specific helper that allows to setup the
                generator.
            target: context or condition for the generation. Defaults to None.

        Returns:
            generator, the detail implementation used for generation.
            If the target is None, the generator is assumed to be untargeted.
        """
        # check if model is downloaded only once.
        if not self.__artifacts_downloaded__:
            logger.debug(
                f"Downloading model: {configuration.algorithm_application}/{configuration.algorithm_version}"
            )
            # download model
            self.local_artifacts = configuration.ensure_artifacts()
            if self.local_artifacts:
                self.__artifacts_downloaded__ = True
        # run model
        return configuration.generate
