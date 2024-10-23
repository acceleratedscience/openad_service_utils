"""This library calls generation processes remotely on a given host"""

import copy
import json
import traceback
import asyncio

import pandas as pd
from pydantic import BaseModel

from openad_service_utils.api.generation.generate_service_defs import (
    create_service_defs, generate_service_defs)
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

    async def route_service(self, request: dict):
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
            if self.property_requestor is None:
                self.property_requestor = request_generation()
            result = await self.property_requestor.request(
                request["service_type"],
                request["parameters"],
                request.get("api_key", ""),
                SAMPLE_SIZE,
            )

        return result

    async def __call__(self, req: dict):
        return await self.route_service(req)


def get_generator_type(generator_application: str, parameters):
    service_list = get_services()
    for service in service_list:
        if (
            generator_application == service["service_type"]
            and service["generator_type"]["algorithm_application"] == parameters["property_type"][0]
        ):
            return service["generator_type"]

    return None


class request_generation:
    models_cache = []

    def __init__(self) -> None:
        pass

    async def request(self, generator_application, parameters: dict, apikey: str, sample_size=10):
        results = []
        logger.debug("generator_application :" + generator_application + " params" + str(parameters))
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
        model = None

        if not model:
            if "target" in parms:
                target = copy.deepcopy(parms["target"])
                parms.pop("target")
                if isinstance(target, list):
                    if len(target) == 1:
                        target = target[0]
                logger.debug(f"running sample: {target=} {parms=} {sample_size=}")
                model = GeneratorRegistry.get_application_instance(**parms, target=target)
            else:
                logger.debug(f"running sample: {parms=} {sample_size=}")
                model = GeneratorRegistry.get_application_instance(**parms)

        # run model inference asynchronously
        result = await self._run_sample(model, sample_size)
        result = pd.DataFrame(result)
        if len(result.columns) == 1:
            result.columns = ["result"]
        return result

    async def _run_sample(self, model, sample_size):
        """Run model sampling in a separate thread to avoid blocking"""
        def run_sample():
            return list(model.sample(sample_size))
        return await asyncio.to_thread(run_sample)
    
    def generate_name(self, params: dict):
        valid_keys = [
            params.get("algorithm_type", ""),
            params.get("algorithm_application", ""),
            params.get("algorithm_name", "")
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

    async def run_tests():
        for request in test_request_generator.tests:
            dt = datetime.now()
            ts = datetime.timestamp(dt)
            if request["service_type"] != "get_crystal_property":
                logger.debug(
                    "\n\n Properties for subject:  " + ", ".join(request["parameters"]["subjects"]) + "   ",
                    datetime.fromtimestamp(ts),
                )
                result = await requestor.route_service(request)
                if result is None:
                    logger.debug("Not Supported")
                else:
                    logger.debug(pd.DataFrame(result))
            else:
                logger.debug("\n\n Properties for crystals")
                logger.debug()
                logger.debug(pd.DataFrame(await requestor.route_service(request)))

    import asyncio
    asyncio.run(run_tests())
