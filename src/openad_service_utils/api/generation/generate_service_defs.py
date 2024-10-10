import copy
import json

from .generation_applications import (ApplicationsRegistry,
                                      get_algorithm_applications)
import logging


# Create a logger
logger = logging.getLogger(__name__)


def generate_service_defs(target_type):

    service_property_blank = {
        "service_type": f"{target_type}_data",
        "description": None,
        "target": {},
        "generator_type": {},
        "algorithm_versions": [],
        "service_name": "",
        "service_description": "",
        "valid_types": [],
        "type_description": {},
        "parameters": [],
        "required_parameters": [],
        "category": "generation",
        "sub_category": "",
        "wheel_package": "",
        "GPU": True,
        "persistent": True,
        "help": "",
    }

    # property_types = PropertyPredictorFactory.keys()
    service_types = {}

    for algorithm in get_algorithm_applications():
        app = ApplicationsRegistry.get_application(
            algorithm_application=algorithm["algorithm_application"],
            domain=algorithm["domain"],
            algorithm_name=algorithm["algorithm_name"],
            algorithm_type=algorithm["algorithm_type"],
        ).configuration_class

        # logger.debug(algorithm["algorithm_name"])

        schema = dict(app.__pydantic_model__.schema())
        # logger.debug(schema)
        property_type = algorithm["algorithm_application"]
        if property_type not in service_types.keys():

            if "properties" in schema.keys():
                if len(schema["properties"].keys()) > 0:
                    service_types[property_type] = {}

                service_types[property_type]["schema"] = schema
                service_types[property_type]["parameters"] = schema["properties"]

                if "required" in schema.keys():
                    #
                    service_types[property_type]["required_parameters"] = schema["required"]
            else:
                service_types["default"].append({property_type: schema})
            service_types[property_type]["generator_type"] = {
                "algorithm_application": algorithm["algorithm_application"],
                "domain": algorithm["domain"],
                "algorithm_name": algorithm["algorithm_name"],
                "algorithm_type": algorithm["algorithm_type"],
            }
            if "algorithm_versions" not in service_types[property_type].keys():
                # logger.debug(property_type)
                service_types[property_type]["algorithm_versions"] = []
        service_types[property_type]["algorithm_versions"].append(algorithm["algorithm_version"])

        try:
            app_inst = ApplicationsRegistry.get_configuration_instance(
                algorithm_application=algorithm["algorithm_application"],
                domain=algorithm["domain"],
                algorithm_name=algorithm["algorithm_name"],
                algorithm_type=algorithm["algorithm_type"],
            )
            app_inst.__init__.__annotations__
        except Exception as e:
            logger.error(e)
            # logger.debug("--------------------------------------------")
            logger.debug("need more installed")

        try:

            # logger.debug("--------------------------------------------")
            # logger.debug("============================================")
            # logger.debug(property_type)
            target_description = app_inst.get_target_description()

            # logger.debug(target_description)
            # logger.debug(app_inst.__doc__)
        except:
            logger.debug("no/;")
            pass
        # logger.debug("============================================")
        # logger.debug("--------------------------------------------")
        service_types[property_type]["target"] = target_description
        service_types[property_type]["description"] = app_inst.__doc__
    prime_list = []

    for x in service_types.keys():

        service_def = copy.deepcopy(service_property_blank)
        service_def["generator_type"] = copy.deepcopy(service_types[x]["generator_type"])

        service_def["target"] = service_types[x]["target"]
        service_def["description"] = service_types[x]["description"]
        service_def["algorithm_versions"].extend(service_types[x]["algorithm_versions"])
        service_def["service_name"] = f"{target_type} with " + x
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
                and xx["generator_type"] == service_def["generator_type"]
            ):
                exists = True
                xx["valid_types"].extend(service_def["valid_types"])
        if not exists:
            prime_list.append(service_def)
    return prime_list

def create_service_defs(target_type, def_locations):
    prime_list = generate_service_defs(target_type)
    i = 0
    for x in prime_list:
        try:
            if len(x["valid_types"]) > 1:
                i += 1
                x["service_name"] = f"{target_type} with " + str(i)
                handle = open(f"{def_locations}/generation_service_defintion_{target_type}s_" + str(i) + ".json", "w")
            else:
                handle = open(
                    f"{def_locations}/generation_service_defintion_{target_type}s_" + x["valid_types"][0] + ".json", "w"
                )
            handle.write(json.dumps(x))
            handle.close()
        except:
            logger.error(str(x))

