import copy
import glob
import json
import os
from pathlib import Path

from pandas import DataFrame
from pydantic import BaseModel
from typing import List, Optional
from collections.abc import Iterable

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
    models_cache = []

    def __init__(self) -> None:
        pass



    def find_requested_models(self, property: str, parameters: dict) -> str:
        """returns a key of the requested model class. detects if user makes changes and want to use a different model"""
        model_key = ""
        # get the predictor class name
        model_class_name = PropertyPredictorRegistry.get_property_predictor_meta_class(property).__name__
        # get the updated parameters
        updated_params = "_".join([str(parameters[x]) for x in sorted(parameters.keys()) if x in ['algorithm_type','domain','algorithm_name','algorithm_version','algorithm_application']])
        if updated_params:
            model_key = model_class_name + "_" + updated_params
        return model_key or model_class_name
    
    def run_prediction(self, service_type, parameters: dict):
        # initialize defaults
        predictor = None
        results = []
        # remove params not needed for model itself
        selected_props: List[str] = parameters.pop("property_type")
        property_type: str = selected_props[0]
        subjects: List[str] = parameters.pop("subjects")
        model_key = self.find_requested_models(property_type, parameters)
        # [print(f"{k}: {v}") for k,v in locals().items()]
        # look through model cache in memory
        for model in self.models_cache:
            if model_key in model:
                # get model from cache
                predictor = model[model_key]
                predictor.selected_properties = selected_props  # update selected properties
                print("[i] getting model from cache: '{}'".format(model_key))
        if predictor is None:
            predictor = PropertyPredictorRegistry.get_property_predictor(
                properties=selected_props, parameters=parameters
            )
            if predictor:
                # add model to cache in memory
                self.models_cache.append({model_key: predictor})
                print("[i] adding model to cache: '{}'".format(model_key))
        # Crystaline structure models take data as file sets, the following manages this for the Crystaline property requests
        if service_type == "get_crystal_property":
            tmpdir_cif = subject_files_repository(
                "cif", subjects
            )
            tmpdir_csv = subject_files_repository(
                "csv", subjects
            )
            if property_type == "metal_nonmetal_classifier" and subjects[
                0
            ].endswith("csv"):
                data_module = Path(tmpdir_csv.name + "/crf_data.csv")
                print(tmpdir_csv.name + "/crf_data.csv")
                result_fields = ["formulas", "predictions"]
            elif not property_type == "metal_nonmetal_classifier" and subjects[
                0
            ].endswith("cif"):
                data_module = Path(tmpdir_cif.name + "/")
                result_fields = ["cif_ids", "predictions"]
            out = predictor(input=data_module)
            pred_dict = dict(zip(out[result_fields[0]], out[result_fields[1]]))
            for key in pred_dict:
                results.append(
                    {
                        "property": property_type,
                        "subject": subjects[0],
                        "key": key,
                        "result": str(pred_dict[key]),
                    }
                )
        else:
            # All other propoerty Requests handled here.
            model_predictions = predictor(subjects)
            results.append(
                        {
                            "properties": selected_props,
                            "subjects": subjects,
                            "results": model_predictions,
                        }
                    )
            # total_length = sum(len(sublist) for sublist in model_predictions)
            # assert total_length == (len(subjects) * len(selected_props)), f"Prediction length mismatch: predictions({total_length}) != expected({len(subjects) * len(selected_props)}). model output: {model_predictions}"
            # # assert len(model_predictions) == len(selected_props), f"Prediction length mismatch: properties({len(model_predictions)}) != expected({len(selected_props)}). make sure to return 1 prediction per property requested. predictions: {model_predictions}"
            # for i, prop in enumerate(selected_props):  # properties are columns
            #     for j, subject in enumerate(subjects):  # subjects are rows
            #         results.append(
            #             {
            #                 "property": prop,
            #                 "subject": subject,
            #                 "result": model_predictions[i][j],
            #             }
            #         )

            # results.append(
            #     {
            #         "subjects": subjects,
            #         "properties": selected_props,
            #         "result": model_predictions,
            #     }
            # )
            # try:
            #     model_predictions = predictor(subjects)
            #     assert len(model_predictions) == (len(subjects) * len(selected_props)), "Prediction length mismatch"
            #     results.append(
            #         {
            #             "subjects": subjects,
            #             "properties": selected_props,
            #             "result": model_predictions,
            #         }
            #     )
            # except Exception:
            #     results.append(
            #         {
            #             "subjects": subjects,
            #             "properties": selected_props,
            #             "result": None,
            #         }
            #     )
        return results

    def request(self, service_type, parameters: dict, apikey: str):
        return self.run_prediction(service_type, parameters)
        results = []
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
                # take parms and concatenate key and value to create a unique model id
                model_key = property_type + "".join([str(parms[x]) for x in parms.keys() if x in ['algorithm_type','domain','algorithm_name','algorithm_version','algorithm_application']])
                # look through model cache in memory
                for model in self.models_cache:
                    if model_key in model:
                        # get model from cache
                        predictor = model[model_key]
                if predictor is None:
                    predictor = PropertyPredictorRegistry.get_property_predictor(
                        name=property_type, parameters=parms
                    )
                    if predictor:
                        # add model to cache in memory
                        self.models_cache.append({model_key: predictor})

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
        print()
        print(locals())
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
