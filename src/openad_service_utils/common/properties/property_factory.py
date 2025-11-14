from enum import Enum
from typing import Any, Dict, List, Tuple, Type, Union

from openad_service_utils.common.algorithms.core import PredictorAlgorithm
from openad_service_utils.common.properties.core import (
    DomainSubmodule,
    PropertyPredictor,
    PropertyPredictorParameters,
)


class PredictorTypes(Enum):
    PROTEIN = "get_protein_property"
    MOLECULE = "get_molecule_property"
    CRYSTAL = "get_crystal_property"
    MESH = "get_mesh_property"


class PropertyFactory:
    """base class to add functionality to PropertyPredictorRegistry"""

    protein_predictors_registry: Dict[
        str,
        Tuple[
            Union[Type[PropertyPredictor], Type[PredictorAlgorithm]],
            Type[PropertyPredictorParameters],
        ],
    ] = {}
    molecule_predictors_registry: Dict[
        str,
        Tuple[
            Union[Type[PropertyPredictor], Type[PredictorAlgorithm]],
            Type[PropertyPredictorParameters],
        ],
    ] = {}
    mesh_predictors_registry: Dict[
        str,
        Tuple[
            Union[Type[PropertyPredictor], Type[PredictorAlgorithm]],
            Type[PropertyPredictorParameters],
        ],
    ] = {}
    crystal_predictors_registry: Dict[
        str,
        Tuple[
            Union[Type[PropertyPredictor], Type[PredictorAlgorithm]],
            Type[PropertyPredictorParameters],
        ],
    ] = {}

    @staticmethod
    def PROPERTY_PREDICTOR_FACTORY() -> (
        Dict[
            str,
            Tuple[
                Union[Type[PropertyPredictor], Type[PredictorAlgorithm]],
                Type[PropertyPredictorParameters],
            ],
        ]
    ):
        return {
            **PropertyFactory.protein_predictors_registry,
            **PropertyFactory.molecule_predictors_registry,
            **PropertyFactory.crystal_predictors_registry,
            **PropertyFactory.mesh_predictors_registry,
        }

    @staticmethod
    def AVAILABLE_PROPERTY_PREDICTORS() -> List[str]:
        return sorted(list(PropertyFactory.PROPERTY_PREDICTOR_FACTORY().keys()))

    @staticmethod
    def AVAILABLE_PROPERTY_PREDICTOR_TYPES() -> List[str]:
        available_types = []
        if PropertyFactory.protein_predictors_registry:
            available_types.append(PredictorTypes.PROTEIN.value)
        if PropertyFactory.molecule_predictors_registry:
            available_types.append(PredictorTypes.MOLECULE.value)
        if PropertyFactory.crystal_predictors_registry:
            available_types.append(PredictorTypes.CRYSTAL.value)
        if PropertyFactory.mesh_predictors_registry:
            available_types.append(PredictorTypes.MESH.value)
        # print("checking available types: ", available_types)
        return available_types

    @staticmethod
    def add_predictor(
        name: str,
        property_type: PredictorTypes,
        predictor: Tuple[
            Union[Type[PropertyPredictor], Type[PredictorAlgorithm]],
            Type[PropertyPredictorParameters],
        ],
    ):
        if property_type == PredictorTypes.PROTEIN:
            PropertyFactory.protein_predictors_registry.update({name: predictor})
        elif property_type == PredictorTypes.MOLECULE:
            PropertyFactory.molecule_predictors_registry.update({name: predictor})
        elif property_type == PredictorTypes.CRYSTAL:
            PropertyFactory.crystal_predictors_registry.update({name: predictor})
        elif property_type == PredictorTypes.MESH:
            PropertyFactory.mesh_predictors_registry.update({name: predictor})
        else:
            raise ValueError(
                f"Property predictor property_type={property_type} not supported. Pick one from class::PredictorTypes"
            )
