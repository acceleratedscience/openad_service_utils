import copy
import glob
import json
import os
from pathlib import Path

from pandas import DataFrame
from pydantic import BaseModel

from openad_service_utils.api.properties.generate_property_service_defs import \
    generate_property_service_defs
# from gt4sd_common.properties import PropertyPredictorRegistry
from openad_service_utils.common.properties import PropertyPredictorRegistry
from openad_service_utils.common.properties.property_factory import \
    PropertyFactory

from .utils import subject_files_repository


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
            print("not valid service " + service["service_name"] + "   " + x)
            return False
    return True


def get_services() -> list:
    all_services = []
    all_services.extend(generate_property_service_defs("molecule", PropertyFactory.molecule_predictors_registry))
    all_services.extend(generate_property_service_defs("protein", PropertyFactory.protein_predictors_registry))
    all_services.extend(generate_property_service_defs("crystal", PropertyFactory.crystal_predictors_registry))
    return all_services


# def get_services() -> list:
#     """pulls the list of available services for"""
#     service_list = []
#     service_files = glob.glob(
#         os.path.abspath(os.path.dirname(new_prop_services.__file__) + "/*.json")
#     )

#     for file in service_files:
#         print(file)
#         with open(file, "r") as file_handle:
#             try:
#                 jdoc = json.load(file_handle)
#                 if is_valid_service(jdoc):
#                     service_list.append(jdoc)
#             except Exception as e:
#                 print(e)
#                 print("invalid service json definition  " + file)
#     return service_list

class service_requester:
    property_requestor = None
    valid_services = ["property", "prediction", "generation", "training"]

    def __init__(self) -> None:
        pass

    def is_valid_service_request(self, request) -> bool:
        return True

    def get_available_services(self):
        return get_services()

    def route_service(self, request):
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
            print("service mismatch")
            return None
        if category == "properties":
            if self.property_requestor is None:
                self.property_requestor = request_properties()
            result = self.property_requestor.request(
                request["service_type"], 
                request["parameters"], 
                request.get("api_key", "")
            )

        return result

    async def __call__(self, req: json):
        req = await req.json()
        return self.route_service(req)


class request_properties:
    PropertyPredictor_cache = []

    def __init__(self) -> None:
        pass

    def request(self, service_type, parameters: dict, apikey: str):
        results = []
        if service_type not in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
            return {f"No service of type {service_type} available "}

        for property_type in parameters["property_type"]:
            predictor = None
            for subject in parameters["subjects"]:
                parms = self.set_parms(property_type, parameters)
                if parms is None:
                    results.append(
                        {
                            "subject": subject,
                            "property": property_type,
                            "result": "check Parameters",
                        }
                    )
                    continue
                # get handle to predictor, if there is not one for the specific propoerty type and Parameter combination then create on
                for handle in self.PropertyPredictor_cache:
                    if (
                        handle["parms"] == parms
                        and handle["property_type"] == property_type
                    ):
                        predictor = handle["predictor"]
                if predictor is None:
                    predictor = PropertyPredictorRegistry.get_property_predictor(
                        name=property_type, parameters=parms
                    )

                    self.PropertyPredictor_cache.append(
                        {
                            "property_type": property_type,
                            "parms": parms,
                            "predictor": predictor,
                        }
                    )

                # Crystaline structure models take data as file sets, the following manages this for the Crystaline property requests
                if service_type == "get_crystal_property":
                    tmpdir_cif = subject_files_repository(
                        "cif", parameters["subjects"]
                    )
                    tmpdir_csv = subject_files_repository(
                        "csv", parameters["subjects"]
                    )

                    if property_type == "metal_nonmetal_classifier" and subject[
                        0
                    ].endswith("csv"):
                        data_module = Path(tmpdir_csv.name + "/crf_data.csv")
                        print(tmpdir_csv.name + "/crf_data.csv")
                        result_fields = ["formulas", "predictions"]
                    elif not property_type == "metal_nonmetal_classifier" and subject[
                        0
                    ].endswith("cif"):
                        data_module = Path(tmpdir_cif.name + "/")
                        result_fields = ["cif_ids", "predictions"]
                    else:
                        continue
                    out = predictor(input=data_module)
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
                    # All other propoerty Requests handled here.
                    try:
                        results.append(
                            {
                                "subject": subject,
                                "property": property_type,
                                "result": predictor(subject),
                            }
                        )
                    except Exception:
                        results.append(
                            {
                                "subject": subject,
                                "property": property_type,
                                "result": None,
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
                    print("no required " + param)
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
    print("Starting", datetime.fromtimestamp(ts))
    import pandas as pd
    import test_request

    requestor = service_requester()
    dt = datetime.now()
    ts = datetime.timestamp(dt)

    print("Service Requestor Loaded ", datetime.fromtimestamp(ts))
    print("----------RUN SERVICES----------------------------------------")

    for request in test_request.tests:
        dt = datetime.now()
        ts = datetime.timestamp(dt)
        if request["service_type"] != "get_crystal_property":
            print(
                "\n\n Properties for subject:  "
                + ", ".join(request["parameters"]["subjects"])
                + "   ",
                datetime.fromtimestamp(ts),
            )
            result = requestor.route_service(request)
            if result is None:
                print("Not Supported")
            else:
                print(pd.DataFrame(result))
        else:
            print("\n\n Properties for crystals")
            print()
            print(pd.DataFrame(requestor.route_service(request)))
