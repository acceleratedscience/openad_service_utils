from typing import Dict, Tuple, Type, Union, Any, List
from openad_service_utils.common.algorithms.core import PredictorAlgorithm
from .core import PropertyPredictor, PropertyPredictorParameters
from enum import Enum

class ProteinPropertyDict:
    """Factory class for creating property predictors."""
    protein_predictors: Dict[str, Tuple[Type[PropertyPredictor], Type[PropertyPredictorParameters]]] = {}

    @classmethod
    def add_property(cls, predictor):
        cls.protein_predictors.update(predictor)


class MoleculePropertyDict:
    """Factory class for creating property predictors."""
    molecule_predictors: Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]] = {}

    @classmethod
    def add_property(cls, predictor):
        cls.molecule_predictors.update(predictor)


class PredictorTypes(Enum):
    PROTEIN = "protein"
    MOLECULE = "molecule"
    CRYSTAL = "crystal"


class PropertyFactory:
    """base class to add functionality to PropertyPredictorRegistry"""
    protein_predictors_registry: Dict[str, Tuple[Type[PropertyPredictor], Type[PropertyPredictorParameters]]] = {}
    molecule_predictors_registry: Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]] = {}
    crystal_predictors_registry: Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]] = {}

    @staticmethod
    def PROPERTY_PREDICTOR_FACTORY() -> Dict[str, Any]:
        return {**PropertyFactory.protein_predictors_registry, **PropertyFactory.molecule_predictors_registry, **PropertyFactory.crystal_predictors_registry}
    
    @staticmethod
    def AVAILABLE_PROPERTY_PREDICTORS() -> Dict[str, Any]:
        return sorted(PropertyFactory.PROPERTY_PREDICTOR_FACTORY().keys())

    @staticmethod
    def AVAILABLE_PROPERTY_PREDICTOR_TYPES() -> List[str]:
        available_types = []
        if PropertyFactory.protein_predictors_registry:
            available_types.append("get_protein_property")
        if PropertyFactory.molecule_predictors_registry:
            available_types.append("get_molecule_property")
        if PropertyFactory.crystal_predictors_registry:
            available_types.append("get_crystal_property")
        return available_types
    
    @staticmethod
    def add_predictor(name: str, property_type: PredictorTypes, predictor: Tuple[Type[PropertyPredictor], Type[PropertyPredictorParameters]]):
        if property_type == PredictorTypes.PROTEIN:
            PropertyFactory.protein_predictors_registry.update({name: predictor})
        elif property_type == PredictorTypes.MOLECULE:
            PropertyFactory.molecule_predictors_registry.update({name: predictor})
        elif property_type == PredictorTypes.CRYSTAL:
            PropertyFactory.crystal_predictors_registry.update({name: predictor})
        else:
            raise ValueError(f"Property predictor name={name} not supported. Pick one from {PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS()}")