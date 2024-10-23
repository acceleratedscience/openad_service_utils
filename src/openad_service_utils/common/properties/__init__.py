#
# MIT License
#
# Copyright (c) 2022 GT4SD team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from typing import Any, Dict, List

from .core import PropertyPredictor
from .property_factory import PropertyFactory
from openad_service_utils.implementation.properties.simple import SimplePredictor

# from ..properties.crystals import CRYSTALS_PROPERTY_PREDICTOR_FACTORY
# from ..properties.molecules import MOLECULE_PROPERTY_PREDICTOR_FACTORY
# from ..properties.proteins import PROTEIN_PROPERTY_PREDICTOR_FACTORY
# from .scorer import (
#     MoleculePropertyPredictorScorer,
#     PropertyPredictorScorer,
#     ProteinPropertyPredictorScorer,
# )

# PROPERTY_FACTORY = PropertyFactory()

# PropertyFactory.PROPERTY_PREDICTOR_FACTORY = PROPERTY_FACTORY.PropertyFactory.PROPERTY_PREDICTOR_FACTORY
# PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS = PROPERTY_FACTORY.PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS

# PROTEIN_PROPERTY_PREDICTOR_FACTORY = PROPERTY_FACTORY.protein_predictors_registry
# MOLECULE_PROPERTY_PREDICTOR_FACTORY = PROPERTY_FACTORY.molecule_predictors_registry
# CRYSTALS_PROPERTY_PREDICTOR_FACTORY = PROPERTY_FACTORY.crystal_predictors_registry

# AVAILABLE_PROPERTY_PREDICTOR_TYPES = PROPERTY_FACTORY.AVAILABLE_PROPERTY_PREDICTOR_TYPES

# SCORING_FACTORY_WITH_PROPERTY_PREDICTORS = {
#     "property_predictor_scorer": PropertyPredictorScorer,
#     "molecule_property_predictor_scorer": MoleculePropertyPredictorScorer,
#     "protein_property_predictor_scorer": ProteinPropertyPredictorScorer,
# }

# AVAILABLE_SCORING_WITH_PROPERTY_PREDICTORS = sorted(
#     SCORING_FACTORY_WITH_PROPERTY_PREDICTORS.keys()
# )
AVAILABLE_SCORING_WITH_PROPERTY_PREDICTORS = {}


class PropertyPredictorRegistry:
    """A registry for property predictors."""
    @staticmethod
    def get_property_predictor_doc_description(name: str) -> Dict[str, Any]:

        try:
            _, parameters_class = PropertyFactory.PROPERTY_PREDICTOR_FACTORY()[name]
            if _.__doc__ is None:
                return "No Description"
            else:
                return _.__doc__
        except KeyError:
            raise ValueError(
                f"Property predictor name={name} not supported. Pick one from {PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS()}"
            )
    
    @staticmethod
    def get_property_predictor_parameters_schema(name: str) -> Dict[str, Any]:
        try:
            _, parameters_class = PropertyFactory.PROPERTY_PREDICTOR_FACTORY()[name]
            return parameters_class.schema_json()
        except KeyError:
            raise ValueError(
                f"Property predictor name={name} not supported. Pick one from {PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS()}"
            )

    @staticmethod
    def get_property_predictor(
        name: str, parameters: Dict[str, Any] = {}
    ) -> PropertyPredictor:
        try:
            property_class, parameters_class = PropertyFactory.PROPERTY_PREDICTOR_FACTORY()[name]
            # pass along chosen property
            parameters["selected_property"] = name
            return property_class(parameters_class(**parameters))
        except KeyError:
            raise ValueError(
                f"Property predictor name={name} not supported. Pick one from {PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS()}"
            )
    
    @staticmethod
    def get_property_predictor_meta_class(
        name: str, parameters: Dict[str, Any] = {}
    ) -> SimplePredictor:
        try:
            property_class, parameters_class = PropertyFactory.PROPERTY_PREDICTOR_FACTORY()[name]
            # pass along chosen property
            parameters["selected_property"] = name
            return property_class
        except KeyError:
            raise ValueError(
                f"Property predictor name={name} not supported. Pick one from {PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS()}"
            )

    @staticmethod
    def get_property_predictor_templates(
        prop_name: str) -> SimplePredictor:
        try:
            property_class, parameters_class = PropertyFactory.PROPERTY_PREDICTOR_FACTORY()[prop_name]
            # pass along chosen property
            return property_class, parameters_class
        except KeyError:
            raise ValueError(
                f"Property predictor name={prop_name} not supported. Pick one from {PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS()}"
            )

    # @staticmethod
    # def get_property_predictor_scorer(
    #     property_name: str,
    #     scorer_name: str,
    #     target: float,
    #     parameters: Dict[str, Any] = {},
    # ) -> PropertyPredictorScorer:
    #     """Get a property predictor scorer.

    #     Args:
    #         property_name: name of the property to score.
    #         scorer_name: name of the scorer to use.
    #         target: target score that will be used to get the distance to the score of a molecule or protein (not be confused with parameters["target"]).
    #         parameters: parameters for the scoring function.

    #     Returns:
    #         A property predictor scorer.
    #     """
    #     scoring_function = PropertyPredictorRegistry.get_property_predictor(
    #         name=property_name, parameters=parameters
    #     )

    #     if scorer_name not in SCORING_FACTORY_WITH_PROPERTY_PREDICTORS:
    #         raise ValueError(
    #             f"Scorer name={scorer_name} not supported. Pick one from {AVAILABLE_SCORING_WITH_PROPERTY_PREDICTORS}"
    #         )
    #     property_predictor_scorer = SCORING_FACTORY_WITH_PROPERTY_PREDICTORS[
    #         scorer_name
    #     ]
    #     return property_predictor_scorer(property_name, scoring_function, target)

    @staticmethod
    def list_available() -> List[str]:
        return PropertyFactory.AVAILABLE_PROPERTY_PREDICTORS()

    @staticmethod
    def list_available_scorers() -> List[str]:
        return AVAILABLE_SCORING_WITH_PROPERTY_PREDICTORS
