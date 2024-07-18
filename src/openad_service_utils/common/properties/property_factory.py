from typing import Dict, Tuple, Type, Union, Any, List
from openad_service_utils.common.algorithms.core import PredictorAlgorithm
from openad_service_utils.common.properties.core import PropertyPredictor, PropertyPredictorParameters, DomainSubmodule
from enum import Enum


class PredictorTypes(Enum):
    PROTEIN = "get_protein_property"
    MOLECULE = "get_molecule_property"
    CRYSTAL = "get_crystal_property"


class PropertyFactory:
    """base class to add functionality to PropertyPredictorRegistry"""
    protein_predictors_registry: Dict[str, Tuple[Type[PropertyPredictor], Type[PropertyPredictorParameters]]] = {}
    molecule_predictors_registry: Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]] = {}
    crystal_predictors_registry: Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]] = {}

    @staticmethod
    def PROPERTY_PREDICTOR_FACTORY() -> Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]]:
        print(PropertyFactory.protein_predictors_registry)
        return {**PropertyFactory.protein_predictors_registry, **PropertyFactory.molecule_predictors_registry, **PropertyFactory.crystal_predictors_registry}
    
    @staticmethod
    def AVAILABLE_PROPERTY_PREDICTORS() -> Dict[str, Any]:
        return sorted(PropertyFactory.PROPERTY_PREDICTOR_FACTORY().keys())

    @staticmethod
    def AVAILABLE_PROPERTY_PREDICTOR_TYPES() -> List[str]:
        available_types = []
        if PropertyFactory.protein_predictors_registry:
            available_types.append(PredictorTypes.PROTEIN.value)
        if PropertyFactory.molecule_predictors_registry:
            available_types.append(PredictorTypes.MOLECULE.value)
        if PropertyFactory.crystal_predictors_registry:
            available_types.append(PredictorTypes.CRYSTAL.value)
        print("checking available types: ", available_types)
        return available_types
    
    @staticmethod
    def add_predictor(name: str, property_type: DomainSubmodule, predictor: Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]):
        if property_type == DomainSubmodule.properties:
            PropertyFactory.protein_predictors_registry.update({name: predictor})
        elif property_type == DomainSubmodule.molecules:
            PropertyFactory.molecule_predictors_registry.update({name: predictor})
        elif property_type == DomainSubmodule.crystals:
            PropertyFactory.crystal_predictors_registry.update({name: predictor})
        else:
            raise ValueError(f"Property predictor domain={property_type} not supported. Pick one from class::DomainSubmodule")
