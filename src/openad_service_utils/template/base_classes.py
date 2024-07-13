# base_classes.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Type, Union
from openad_service_utils.common.algorithms.core import AlgorithmConfiguration, GeneratorAlgorithm, Targeted, Untargeted
from openad_service_utils import ApplicationsRegistry


# leave typing generic for algorithm implementation
S = TypeVar("S")  # used for generated items
T = TypeVar("T")  # used for target of generation
U = TypeVar("U")  # used for additional context (e.g. part of target definition)


class BaseGenerator(ABC):
    @abstractmethod
    def __init__(self, resources_path: str, **kwargs):
        self.resources_path = resources_path

    @abstractmethod
    def generate(
        self,
        target: Optional[T],
    ) -> List[Any]:
        pass

    def validate_configuration(
        self, configuration: AlgorithmConfiguration
    ) -> AlgorithmConfiguration:
        assert isinstance(configuration, AlgorithmConfiguration)
        return configuration


class BaseConfiguration(AlgorithmConfiguration[S, T]):
    """Algorithm parameter definitions and implementation setup.

    The signature of this class constructor (given by the instance attributes) is used
    for the REST API and needs to be serializable.

    Child classes will add additional instance attributes to configure their respective
    algorithms. This will require setting default values for all of the attributes defined
    here.
    However, the values for :attr:`algorithm_name` and :attr:`algorithm_application`
    are set when you register the application.
    """
    @abstractmethod
    def get_target_description(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def get_conditional_generator(self) -> BaseGenerator:
        """return your BaseGenerator"""
        pass

    @classmethod
    def register(cls):
        """Register the configuration with the ApplicationsRegistry and load the model into runtime."""
        ApplicationsRegistry.register_algorithm_application(cls.algorithm_class)(cls)


class BaseAlgorithm(GeneratorAlgorithm[S, T]):
    """Interface for automated generation via an :class:`BaseConfiguration`."""
    def __init__(
        self, configuration: BaseConfiguration[S, T], target: Optional[T] = None
    ):
        configuration = self.validate_configuration(configuration)
        super().__init__(configuration=configuration, target=target)

    def get_generator(
        self,
        configuration: BaseConfiguration[S, T],
        target: Optional[T],
    ) -> Union[Untargeted, Targeted[T]]:
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
        self.local_artifacts = configuration.ensure_artifacts()
        implementation: BaseGenerator = configuration.get_conditional_generator(self.local_artifacts)
        return implementation.generate
