import copy
import json
from pathlib import Path

from pydantic import BaseModel
from openad_service_utils.utils.convert import json_string_to_dict
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.api.cache import get_model_cache, conditional_lru_cache
from openad_service_utils.api.properties.generate_property_service_defs import (
    generate_property_service_defs,
)

# from gt4sd_common.properties import PropertyPredictorRegistry
from openad_service_utils.common.properties import PropertyPredictorRegistry
from openad_service_utils.common.properties.property_factory import PropertyFactory

from .utils import subject_files_repository
import logging
from openad_service_utils.utils.logging_config import setup_logging

# Set up logging configuration
setup_logging()

# Create a logger
logger = logging.getLogger(__name__)


class Info(BaseModel):
    conf_one: float
    conf_two: str
    conf_three: bool

    class Config:
        extra = "forbid"


class ConfStructure(BaseModel):
    version: int
    info: Info


def is_valid_service(service: dict):
    "to be completed"
    required_fields = [
        "service_name",
        "service_type",
        "parameters",
        "required_parameters",
        "category",
        "sub_category",
        "wheel_package",
        "GPU",
        "persistent",
        "help",
    ]

    for x in required_fields:
        if x not in service.keys():
            logger.debug("not valid service " + service["service_name"] + "   " + x)
            return False
    return True


def get_services() -> list:
    all_services = []
    all_services.extend(
        generate_property_service_defs(
            "molecule", PropertyFactory.molecule_predictors_registry
        )
    )
    all_services.extend(
        generate_property_service_defs(
            "protein", PropertyFactory.protein_predictors_registry
        )
    )
    all_services.extend(
        generate_property_service_defs(
            "crystal", PropertyFactory.crystal_predictors_registry
        )
    )
    return all_services


class service_requester:
    property_requestor = None
    valid_services = ["property", "prediction", "generation", "training"]

    def __init__(self) -> None:
        pass

    def is_valid_service_request(self, request) -> bool:
        return True

    def get_available_services(self):
        return get_services()

    @conditional_lru_cache(maxsize=100)
    def route_service(self, request):
        if get_config_instance().ENABLE_CACHE_RESULTS:
            request = json_string_to_dict(request)
        result = None
        if not self.is_valid_service_request(request):
            return False
        category = None

        for service in get_services():
            current_service = None

            if (
                service["service_type"] == request["service_type"]
                and service["service_name"] == request["service_name"]
            ):
                category = service["category"]
                current_service = service
                break

        if current_service is None:
            logger.debug("service mismatch")
            return None
        if category == "properties":
            if self.property_requestor is None:
                self.property_requestor = request_properties()
            result = self.property_requestor.request(
                request["service_type"],
                request["parameters"],
                request.get("api_key", ""),
            )

        return result

    async def __call__(self, req: json):
        req = await req.json()
        return self.route_service(req)


class request_properties:
    def __init__(self) -> None:
        self.model_cache = get_model_cache()

    def request(self, service_type, parameters: dict, apikey: str):
        results = []
        if service_type not in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
            return {f"No service of type {service_type} available "}

        for property_type in parameters["property_type"]:
            predictor = None
            for subject in parameters["subjects"]:
                parms = self.set_parms(property_type, parameters)
                parms["selected_property"] = property_type
                if parms is None:
                    results.append(
                        {
                            "subject": subject,
                            "property": property_type,
                            "result": "check Parameters",
                        }
                    )
                    continue
                # take parms and concatenate key and value to create a unique model id
                using_model = property_type + "".join(
                    [
                        str(type(parms[x])) + str(parms[x])
                        for x in parms.keys()
                        if x
                        in [
                            "algorithm_type",
                            "domain",
                            "algorithm_name",
                            "algorithm_version",
                            "algorithm_application",
                        ]
                    ]
                )
                try:
                    # Try to get model from cache
                    predictor = self.model_cache.get(using_model)
                    
                    if predictor is None:
                        predictor = PropertyPredictorRegistry.get_property_predictor(
                            name=property_type, parameters=parms
                        )
                    else:
                        # Update model params if needed
                        logger.debug(f"Using cached model with key: {using_model}")
                        pydantic_params = (
                            PropertyPredictorRegistry.get_property_predictor_meta_params(
                                name=property_type
                            )
                        )
                        predictor._update_parameters(pydantic_params(**parms))
                except Exception as e:
                    logger.error(f"Error handling model cache: {str(e)}")
                    # Fallback to creating new model without caching
                    predictor = PropertyPredictorRegistry.get_property_predictor(
                        name=property_type, parameters=parms
                    )

                # Crystaline structure models take data as file sets, the following manages this for the Crystaline property requests
                if service_type == "get_crystal_property":
                    tmpdir_cif = subject_files_repository("cif", parameters["subjects"])
                    tmpdir_csv = subject_files_repository("csv", parameters["subjects"])

                    if property_type == "metal_nonmetal_classifier" and subject[
                        0
                    ].endswith("csv"):
                        data_module = Path(tmpdir_csv.name + "/crf_data.csv")
                        logger.debug(tmpdir_csv.name + "/crf_data.csv")
                        result_fields = ["formulas", "predictions"]
                    elif not property_type == "metal_nonmetal_classifier" and subject[
                        0
                    ].endswith("cif"):
                        data_module = Path(tmpdir_cif.name + "/")
                        result_fields = ["cif_ids", "predictions"]
                    else:
                        continue
                    out = predictor(data_module)
                    pred_dict = dict(zip(out[result_fields[0]], out[result_fields[1]]))
                    for key in pred_dict:
                        results.append(
                            {
                                "subject": subject[0],
                                "property": property_type,
                                "key": key,
                                "result": str(pred_dict[key]),
                            }
                        )

                else:
                    # All other property Requests handled here.
                    result = predictor(subject)
                    
                    # Now that model is loaded and used, try to cache it
                    if predictor and not self.model_cache.get(using_model):
                        logger.debug(f"Adding model to cache with key: {using_model}")
                        self.model_cache.set(using_model, predictor)
                    
                    results.append(
                        {
                            "subject": subject,
                            "property": property_type,
                            "result": result,
                        }
                    )
        return results

    def set_parms(self, property_type, parameters):
        request_params = {}
        schema = PropertyPredictorRegistry.get_property_predictor_parameters_schema(
            property_type
        )
        schema = json.loads(schema)
        if "required" in schema.keys():
            for param in schema["required"]:
                if param in ["property_type", "subjects", "subject_type"]:
                    continue
                elif param in parameters.keys():
                    continue
                else:
                    logger.debug("no required " + param)
                    return None
        for param in parameters.keys():
            if param in ["property_type", "subjects", "subject_type"]:
                continue

            request_params[param] = parameters[param]

        return copy.deepcopy(request_params)

    def algorithm_is_valid(self, algorithm, algorithm_version):
        return True


# app = service_requester.options(route_prefix="/route_service").bind()

if __name__ == "__main__":
    from datetime import datetime

    dt = datetime.now()
    ts = datetime.timestamp(dt)
    logger.debug("Starting", datetime.fromtimestamp(ts))
    import pandas as pd
    import test_request

    requestor = service_requester()
    dt = datetime.now()
    ts = datetime.timestamp(dt)

    logger.debug("Service Requestor Loaded ", datetime.fromtimestamp(ts))
    logger.debug("----------RUN SERVICES----------------------------------------")

    for request in test_request.tests:
        dt = datetime.now()
        ts = datetime.timestamp(dt)
        if request["service_type"] != "get_crystal_property":
            logger.debug(
                "\n\n Properties for subject:  "
                + ", ".join(request["parameters"]["subjects"])
                + "   ",
                datetime.fromtimestamp(ts),
            )
            result = requestor.route_service(request)
            if result is None:
                logger.debug("Not Supported")
            else:
                logger.debug(pd.DataFrame(result))
        else:
            logger.debug("\n\n Properties for crystals")
            logger.debug()
            logger.debug(pd.DataFrame(requestor.route_service(request)))
