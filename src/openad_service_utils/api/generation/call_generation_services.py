"""This library calls generation processes remotely on a given host"""

import json
from openad_service_utils.api.generation.generate_service_defs import generate_service_defs, create_service_defs
import copy
import pandas as pd
from .generation_applications import ApplicationsRegistry as GeneratorRegistry
from .generation_applications import get_algorithm_applications
from openad_service_utils.common.exceptions import InvalidItem
import traceback

# from ray import serve
from pydantic import BaseModel

# print(get_algorithm_applications())

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
            print("not valid service " + service["service_name"] + "   " + x)
            return False
    return True


# def get_services() -> list:
#     """pulls the list of available services for"""
#     service_list = []
#     service_files = glob.glob(os.path.abspath(os.path.dirname(new_prop_services.__file__) + "/*.json"))

#     for file in service_files:
#         # print(file)
#         with open(file, "r") as file_handle:
#             try:
#                 jdoc = json.load(file_handle)
#                 if is_valid_service(jdoc):
#                     service_list.append(jdoc)
#             except Exception as e:
#                 print(e)
#                 print("invalid service json definition  " + file)
#     return service_list

ALL_AVAILABLE_SERVICES = []

def get_services() -> list:
    """pulls the list of available services once server is ready"""
    global ALL_AVAILABLE_SERVICES
    if not ALL_AVAILABLE_SERVICES:
        print("getting services")
        ALL_AVAILABLE_SERVICES = generate_service_defs("generate")
    return ALL_AVAILABLE_SERVICES


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
            print("service mismatch")
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
            and service["generator_type"]["algorithm_application"] == parameters["property_type"][0]
        ):
            print("Generator")
            print(service)
            return service["generator_type"]

    return None


class request_generation:
    Generator_cache = []

    def __init__(self) -> None:
        pass

    def request(self, generator_application, parameters: dict, apikey: str, sample_size=10):
        results = []
        print("generator_application :" + generator_application + " params" + str(parameters))
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
        try:
            parms = self.set_parms(generator_type=generator_type, parameters=parameters)
        except Exception as e:
            result = {"exception": str(e)}
            result = {"error": result}
            return result

        print(generator_type)
        parms.update(generator_type)
        print(parms)

        try:
            if "target" in parms:
                target = copy.deepcopy(parms["target"])
                parms.pop("target")
                if isinstance(target, list):
                    if len(target) == 1:
                        target = target[0]
                print("-----------------------------------------")
                print(parms)
                print("-----------------------------------------")
                print(target)
                print(sample_size)
                print("-----------------------------------------")

                model = GeneratorRegistry.get_application_instance(**parms, target=target)
            else:
                model = GeneratorRegistry.get_application_instance(**parms)
        except TypeError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Type Error: ": str(e)}}
        except IndexError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Module Index Error: ": str(e)}}
        except InvalidItem as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Invaliditem: ": str(e)}}
        except ValueError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Incorrect value: ": str(e)}}
        except OSError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"OS ERROR: ": str(e)}}
        except Exception as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Unknown Error": str(e)}}

        try:
            result = list(model.sample(sample_size))
            # return result
            result = pd.DataFrame(result)
            if len(result.columns) == 1:
                result.columns = ["result"]
            return result
        except TypeError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Type Error: ": str(e)}}
        except IndexError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Module Index Error: ": str(e)}}
        except InvalidItem as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Invaliditem: ": str(e)}}
        except ValueError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Incorrect value: ": str(e)}}
        except OSError as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"OS ERROR: ": str(e)}}
        except Exception as e:
            print(traceback.print_tb(e.__traceback__))
            return {"error": {"Unknown Error": str(e)}}

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
                    print("no required " + param)
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
    print("Starting", datetime.fromtimestamp(ts))
    import test_request_generator
    import pandas as pd

    requestor = service_requester()
    dt = datetime.now()
    ts = datetime.timestamp(dt)

    print("Service Requestor Loaded ", datetime.fromtimestamp(ts))
    print("----------RUN SERVICES----------------------------------------")

    for request in test_request_generator.tests:
        dt = datetime.now()
        ts = datetime.timestamp(dt)
        if request["service_type"] != "get_crystal_property":
            print(
                "\n\n Properties for subject:  " + ", ".join(request["parameters"]["subjects"]) + "   ",
                datetime.fromtimestamp(ts),
            )
            result = requestor.route_service(request)
            if result == None:  # noqa: E711
                print("Not Supported")
            else:
                print(pd.DataFrame(result))
        else:
            print("\n\n Properties for crystals")
            print()
            print(pd.DataFrame(requestor.route_service(request)))
