from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
# from call_property_services import service_requester, get_services
# from bmfm_inference_service.services.call_property_services import service_requester, get_services  # noqa: E402
from openad_service_utils.api.generation.call_generation_services import service_requester as generation_request  # noqa: E402
from openad_service_utils.api.generation.call_generation_services import get_services as get_generation_services  # noqa: E402
from openad_service_utils.api.properties.call_property_services import service_requester as property_request
from openad_service_utils.api.properties.call_property_services import get_services as get_property_services
from pandas import DataFrame
from openad_service_utils.common.properties.property_factory import PropertyFactory

app = FastAPI()

gen_requester = generation_request()
prop_requester = property_request()


@app.get("/health", response_class=HTMLResponse)
async def health():
    return "UP"


@app.post("/service")
async def service(property_request: dict):
    if property_request.get("service_type") in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
        result = prop_requester.route_service(property_request)
    else: # !TODO implement logic for checking generation requests
        result = gen_requester.route_service(property_request)
    if isinstance(result, DataFrame):
        return result.to_dict(orient="records")
    else:
        return result


@app.get("/service")
async def get_service_defs():
    """return service definitions"""
    # get service list
    services: list = get_generation_services()
    services.extend(get_property_services())
    return JSONResponse(services)


def start_server(host="0.0.0.0", port=8080, log_level="debug"):
    import uvicorn

    # import torch
    # if torch.cuda.is_available():
    #     print(f"\n[i] cuda is available: {torch.cuda.is_available()}")
    #     print(f"[i] cuda version: {torch.version.cuda}\n")
    #     print(f"[i] device name: {torch.cuda.get_device_name(0)}")
    #     print(f"[i] torch version: {torch.__version__}\n")
    uvicorn.run(app, host=host, port=port, log_level=log_level, workers=1)


if __name__ == "__main__":
    start_server()
