# simple.py
# follows a simpler gt4sd registry pattern

from abc import ABC, abstractmethod
from typing import Any, List, Optional, TypeVar, ClassVar
from openad_service_utils.common.algorithms.core import AlgorithmConfiguration, GeneratorAlgorithm, Targeted, Untargeted
from openad_service_utils import ApplicationsRegistry


# leave typing generic for algorithm implementation
S = TypeVar("S")  # used for generated items
T = TypeVar("T")  # used for target of generation
U = TypeVar("U")  # used for additional context (e.g. part of target definition)


class SimpleGenerator(AlgorithmConfiguration[S, T], ABC):
    """More simple implementation of :class:`BaseConfiguration`

    The signature of this class constructor (given by the instance attributes) is used
    for the REST API and needs to be serializable.
    However, the values for :attr:`algorithm_application`
    are set when you register the application based on the child class name.

    1. Setup your generator. Ease child implementation. For example::

        from openad_service_utils.implementation.generation import SimpleGenerator

        class YourApplicationName(SimpleGenerator):
            algorithm_type: str = "conditional_generation"
            algorithm_name = "MyGeneratorAlgorithm"
            algorithm_version: str = "v0"
            domain: str = "materials"

            actual_parameter1: float = 1.61
            actual_parameter2: float = 1.61
            ...

            # no __init__ definition required
        def generate(self, target: Optional[T]) -> List[Any]:
            # implementation goes here
            pass
    
    2. Register the generator with the ApplicationsRegistry::

        YourApplicationName.register()
    """
    algorithm_name: ClassVar[str]
    __artifacts_downloaded__: bool = False

    @classmethod
    def register(cls):
        """Register the configuration with the ApplicationsRegistry and load the model into runtime."""
        required = ["algorithm_name", "algorithm_type"]
        for field in required:
            if field not in cls.__dict__:
                raise TypeError(f"Can't instantiate class ({cls.__name__}) without '{field}' class variable")
        # create during runtime so that user doesnt have to write separate class
        algorithm = type(cls.algorithm_name, (BaseAlgorithm,), {})
        print(f"[i] registering simple generator: {'/'.join([cls.algorithm_type, cls.algorithm_name, cls.__name__, cls.algorithm_version])}\n")
        ApplicationsRegistry.register_algorithm_application(algorithm)(cls)
    
    @abstractmethod
    def generate(
        self,
        target: Optional[T],
    ) -> List[Any]:
        pass


class BaseAlgorithm(GeneratorAlgorithm[S, T]):
    """Interface for automated generation via an :class:`SimpleGenerator`."""
    def __init__(
        self, configuration: SimpleGenerator[S, T], target: Optional[T] = None
    ):
        super().__init__(configuration=configuration, target=target)

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
        if configuration.__artifacts_downloaded__:
            # download model
            self.local_artifacts = configuration.ensure_artifacts()
            if self.local_artifacts:
                configuration.__artifacts_downloaded__ = True
        # run model
        return configuration.generate