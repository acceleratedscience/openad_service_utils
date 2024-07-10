# base_classes.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from openad_service_utils.algorithms.core import AlgorithmConfiguration, GeneratorAlgorithm, Targeted, Untargeted

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

class BaseAlgorithm(GeneratorAlgorithm[S, T]):
    def __init__(
        self, configuration: AlgorithmConfiguration[S, T], target: Optional[T] = None
    ):
        configuration = self.validate_configuration(configuration)
        super().__init__(configuration=configuration, target=target)

    def get_generator(
        self,
        configuration: AlgorithmConfiguration[S, T],
        target: Optional[T],
    ) -> Targeted[T]:
        """Get the function to from generator.

        Args:
            configuration: helps to set up the application.
            target: context or condition for the generation. Just an optional string here.

        Returns:
            callable generating a list of 1 item containing salutation and temperature converted to fahrenheit.
        """
        self.local_artifacts = configuration.ensure_artifacts()
        implementation = configuration.get_conditional_generator(self.local_artifacts)
        # implementation = configuration.get_conditional_generator(self.local_artifacts)
        return implementation.generate

    def validate_configuration(
        self, configuration: AlgorithmConfiguration
    ) -> AlgorithmConfiguration:
        assert isinstance(configuration, AlgorithmConfiguration)
        return configuration

class BaseConfiguration(AlgorithmConfiguration[S, T]):
    @abstractmethod
    def get_target_description(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def get_conditional_generator(self) -> BaseGenerator:
        """should match BaseGenerator.generate signature"""
        pass