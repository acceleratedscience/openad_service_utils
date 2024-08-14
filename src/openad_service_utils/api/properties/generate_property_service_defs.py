import copy
import json
from typing import Any, Dict, List

from openad_service_utils.common.properties import PropertyPredictorRegistry
from openad_service_utils.implementation.properties.simple import PropertyInfo


def description_builder(property_list: List[PropertyInfo]):
    text = ""
    for item in property_list:
        text = text + f"Property: <cmd>{item['name']}</cmd>\nDescription:\n{item.get('description', 'No Description')}\n"
    return text


def generate_property_service_defs(target_type: str, PropertyPredictorFactory: Dict[str, Any]):
    if target_type == "molecule":
        input_type = "SMILES"
    elif target_type == "protein":
        input_type = "PROTEIN"
    else:
        input_type = "directory"

    service_property_blank = {
        "service_type": f"get_{target_type}_property",
        "service_name": "",
        "subject": input_type,
        "description": "Returns a given Property Type for: \n",
        "valid_types": [],
        "type_description": {},
        "parameters": [],
        "required_parameters": [],
        "category": "properties",
        "sub_category": "",
        "wheel_package": "",
        "GPU": False,
        "persistent": True,
        "help": "",
    }

    property_types = PropertyPredictorFactory.keys()
    service_types = {"default": []}

    for property_type in property_types:
        schema = json.loads(PropertyPredictorRegistry.get_property_predictor_parameters_schema(property_type))

        if "properties" in schema.keys():
            if len(schema["properties"].keys()) > 0:
                service_types[property_type] = {}
            else:
                service_types["default"].append({property_type: schema})
                continue

            service_types[property_type]["schema"] = schema
            service_types[property_type]["parameters"] = schema["properties"]
            
            if service_types[property_type]["parameters"]:
                # remove redundant field. available_properties -> valid_types
                property_data_schema = service_types[property_type]["parameters"].pop("available_properties", {}).get("default", [])

            # service_types["description"] = "Retrieves  properties for valid property types\n"
            # service_types["description_details"] = "Retrieves  properties for valid property types\n"
            if "required" in schema.keys():
                #
                service_types[property_type]["required_parameters"] = schema["required"]

        else:
            service_types["default"].append({property_type: schema})
        for param in service_types[property_type]["parameters"].keys():
            if "allOf" in service_types[property_type]["parameters"][param]:
                service_types[property_type]["parameters"][param]["allOf"] = "qualified directory"
    prime_list = []
    for x in service_types.keys():
        service_def = copy.deepcopy(service_property_blank)

        if x == "default":
            service_def["service_name"] = f"get {target_type} properties"

            valid_types = []
            for y in service_types[x]:
                for yy in y.keys():
                    valid_types.append(yy)
                    service_def["description"] = (
                        service_def["description"]
                        + f"  -<cmd>{yy}</cmd>"
                        + ": "
                        + PropertyPredictorRegistry.get_property_predictor_doc_description(yy)
                        + "\n"
                    )
            service_def["valid_types"] = copy.deepcopy(valid_types)
            # skip empty defs
            if len(valid_types) == 0:  # !info check this logic
                continue
        else:
            # todo: too hacky. simplify.
            meta_class_name = PropertyPredictorRegistry.get_property_predictor_meta_class(name=x, parameters={})
            service_def["service_name"] = f"get {target_type} " + meta_class_name.algorithm_application
            description = description_builder(property_data_schema)
            service_def["description"] = description or (
                service_def["description"]
                + f"  -<cmd>{x}</cmd>"
                + ": "
                + PropertyPredictorRegistry.get_property_predictor_doc_description(x)
                + "\n"
            )
            valid_types = [x]
            service_def["valid_types"] = copy.deepcopy(valid_types)
            if "required_parameters" in service_types[x].keys():
                service_def["required_parameters"] = service_types[x]["required_parameters"]
            if "parameters" in service_types[x].keys():
                service_def["parameters"] = service_types[x]["parameters"]
        service_def["sub_category"] = f"{target_type}s"
        exists = False
        for xx in prime_list:
            if (
                xx["parameters"] == service_def["parameters"]
                and xx["required_parameters"] == service_def["required_parameters"]
            ):
                exists = True
                xx["valid_types"].extend(service_def["valid_types"])
        if not exists:
            prime_list.append(service_def)
    return prime_list
    
def create_property_defs(target_type, PropertyPredictorFactory, services_path):
    prime_list = generate_property_service_defs(target_type, PropertyPredictorFactory)
    i = 0
    for x in prime_list:
        if len(x["valid_types"]) == 0:
            continue
        if len(x["valid_types"]) > 1:
            i += 1
            x["service_name"] = f"get {target_type} properties " + str(i)
            handle = open(
                f"{services_path}/property_service_defintion_{target_type}s_" + str(i) + ".json",
                "w",
            )
        else:
            handle = open(
                f"{services_path}/property_service_defintion_{target_type}s_" + x["valid_types"][0] + ".json",
                "w",
            )
        handle.write(json.dumps(x, indent=2))
        handle.close()


if __name__ == "__main__":
    from openad_service_utils.common.properties.property_factory import \
        PropertyFactory

    # import os
    # import definitions.services as new_prop_services
    # services_path = os.path.abspath(os.path.dirname(new_prop_services.__file__))
    services_path = "./"
    create_property_defs("molecule", PropertyFactory.molecule_predictors_registry, services_path)
    create_property_defs("protein", PropertyFactory.protein_predictors_registry, services_path)
