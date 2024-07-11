from typing import Dict, Tuple, Type, Union, Any, List
from openad_service_utils.common.algorithms.core import PredictorAlgorithm
from .core import PropertyPredictor, PropertyPredictorParameters


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


class PropertyFactory:
    """base class to add functionality to PropertyPredictorRegistry"""
    protein_predictors_registry: Dict[str, Tuple[Type[PropertyPredictor], Type[PropertyPredictorParameters]]] = {}
    molecule_predictors_registry: Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]] = {}
    crystal_predictors_registry: Dict[str, Tuple[Union[Type[PropertyPredictor], Type[PredictorAlgorithm]], Type[PropertyPredictorParameters]]] = {}

    @property
    def PROPERTY_PREDICTOR_FACTORY(self) -> Dict[str, Any]:
        return {**self.protein_predictors_registry, **self.molecule_predictors_registry, **self.crystal_predictors_registry}
    
    @property
    def AVAILABLE_PROPERTY_PREDICTORS(self) -> Dict[str, Any]:
        return sorted(self.PROPERTY_PREDICTOR_FACTORY.keys())

    @property
    def AVAILABLE_PROPERTY_PREDICTOR_TYPES(self) -> List[str]:
        available_types = []
        if self.protein_predictors_registry:
            available_types.append("get_protein_property")
        if self.molecule_predictors_registry:
            available_types.append("get_molecule_property")
        if self.crystal_predictors_registry:
            available_types.append("get_crystal_property")
        return available_types