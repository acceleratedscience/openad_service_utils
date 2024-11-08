import json

def dict_to_json_string(d: dict) -> str:
    return json.dumps(d, sort_keys=True)

def json_string_to_dict(json_string: str) -> dict:
    return json.loads(json_string)