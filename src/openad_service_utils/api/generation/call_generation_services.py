"""This library calls generation processes remotely on a given host"""

import copy
import json
import traceback

import pandas as pd
from pydantic import BaseModel

from openad_service_utils.api.generation.generate_service_defs import (
    create_service_defs,
    generate_service_defs,
)
from openad_service_utils.common.exceptions import InvalidItem

from .generation_applications import ApplicationsRegistry as GeneratorRegistry
from .generation_applications import get_algorithm_applications
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


docking_props = ["molecule_one", "askcos", "docking"]


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
            logger.error("not valid service " + service["service_name"] + "   " + x)
            return False
    return True


# def get_services() -> list:
#     """pulls the list of available services for"""
#     service_list = []
#     service_files = glob.glob(os.path.abspath(os.path.dirname(new_prop_services.__file__) + "/*.json"))

#     for file in service_files:
#         # logger.debug(file)
#         with open(file, "r") as file_handle:
#             try:
#                 jdoc = json.load(file_handle)
#                 if is_valid_service(jdoc):
#                     service_list.append(jdoc)
#             except Exception as e:
#                 logger.debug(e)
#                 logger.debug("invalid service json definition  " + file)
#     return service_list

ALL_AVAILABLE_SERVICES = []


def get_services() -> list:
    """pulls the list of available services once server is ready"""
    # !TODO: FIX THIS UGLY LOGIC
    global ALL_AVAILABLE_SERVICES
    if not ALL_AVAILABLE_SERVICES:
        ALL_AVAILABLE_SERVICES = generate_service_defs("generate")
    return ALL_AVAILABLE_SERVICES.copy()


class service_requester:
    property_requestor = None
    valid_services = ["property", "prediction", "generation", "training"]

    def __init__(self) -> None:
        pass

    def is_valid_service_request(self, request) -> bool:
        return True

    def get_available_services(self):
        """fetch available services and cache results"""
        return get_services()

    def route_service(self, request: dict):
        result = None
        if not self.is_valid_service_request(request):
            return False
        category = None

        current_service = None
        for service in get_services():
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
        if current_service["service_name"] in []:
            return [current_service["service_name"] + "   Not Currently Available"]

        if "sample_size" in request:
            try:
                SAMPLE_SIZE = int(request["sample_size"])
            except:
                SAMPLE_SIZE = 10
        else:
            SAMPLE_SIZE = 10

        if category == "generation":
            if self.property_requestor == None:  # noqa: E711
                self.property_requestor = request_generation()
            result = self.property_requestor.request(
                request["service_type"],
                request["parameters"],
                request.get("api_key", ""),
                SAMPLE_SIZE,
            )

        return result

    async def __call__(self, req: json):
        req = await req.json()
        return self.route_service(req)


def get_generator_type(generator_application: str, parameters):
    service_list = get_services()
    for service in service_list:
        if (
            generator_application == service["service_type"]
            and service["generator_type"]["algorithm_application"]
            == parameters["property_type"][0]
        ):
            return service["generator_type"]

    return None


class request_generation:
    models_cache = []

    def __init__(self) -> None:
        pass

    def request(
        self, generator_application, parameters: dict, apikey: str, sample_size=10
    ):
        results = []
        logger.debug(
            "generator_application :"
            + generator_application
            + " params"
            + str(parameters)
        )
        generator_type = get_generator_type(generator_application, parameters)
        if len(parameters["subjects"]) > 0:
            subject = parameters["subjects"][0]
        else:
            subject = None
        if generator_type is None:
            results.append(
                {
                    "subject": subject,
                    "generator": generator_application,
                    "result": "check Parameters",
                }
            )
        # TODO: validate
        parms = self.set_parms(generator_type=generator_type, parameters=parameters)

        parms.update(generator_type)
        # take parms and concatenate key and value to create a unique model id
        model = None
        # TODO: fix model cache
        # model_type = generator_application + "_" + "_".join([str(parms[x]) for x in parms.keys() if x in ['algorithm_type','domain','algorithm_name','algorithm_version','algorithm_application']])
        # logger.debug(f"model cache lookup key: {model_type}")
        # for model in self.models_cache:
        #     if model_type in model:
        #         model = model[model_type]

        if not model:
            if "target" in parms:
                target = copy.deepcopy(parms["target"])
                parms.pop("target")
                if isinstance(target, list):
                    if len(target) == 1:
                        target = target[0]
                logger.debug(f"running sample: {target=} {parms=} {sample_size=}")
                model = GeneratorRegistry.get_application_instance(
                    **parms, target=target
                )
                # self.models_cache.append({model_type: model})
            else:
                logger.debug(f"running sample: {parms=} {sample_size=}")
                model = GeneratorRegistry.get_application_instance(**parms)
                # self.models_cache.append({model_type: model})

        # run model inference
        result = list(model.sample(sample_size))
        # return result
        result = pd.DataFrame(result)
        if len(result.columns) == 1:
            result.columns = ["result"]
        return result

    def generate_name(self, params: dict):
        valid_keys = [
            params.get("algorithm_type", ""),
            params.get("algorithm_application", ""),
            params.get("algorithm_name", ""),
        ]
        return valid_keys

    def set_parms(self, generator_type, parameters):
        request_params = {}
        service_list = get_services()
        for service in service_list:
            if generator_type == service["generator_type"]["algorithm_application"]:
                break

        if "required" in service.keys():
            for param in service["required"]:
                if param in ["subjects", "subject_type"]:
                    continue
                elif param in parameters.keys():
                    continue
                else:
                    logger.debug("no required " + param)
                    return None
        for param in parameters.keys():
            if param == "subjects":
                if len(parameters[param]) > 0:
                    request_params["target"] = parameters[param]
                continue
            if param in ["subject_type", "property_type"]:
                continue

            request_params[param] = parameters[param]

        return copy.deepcopy(request_params)


if __name__ == "__main__":
    from datetime import datetime

    dt = datetime.now()
    ts = datetime.timestamp(dt)
    logger.debug("Starting", datetime.fromtimestamp(ts))
    import pandas as pd
    import test_request_generator

    requestor = service_requester()
    dt = datetime.now()
    ts = datetime.timestamp(dt)

    logger.debug("Service Requestor Loaded ", datetime.fromtimestamp(ts))
    logger.debug("----------RUN SERVICES----------------------------------------")

    for request in test_request_generator.tests:
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
            if result == None:  # noqa: E711
                logger.debug("Not Supported")
            else:
                logger.debug(pd.DataFrame(result))
        else:
            logger.debug("\n\n Properties for crystals")
            logger.debug()
            logger.debug(pd.DataFrame(requestor.route_service(request)))
