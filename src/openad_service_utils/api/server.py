from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from openad_service_utils.api.generation.call_generation_services import service_requester as generation_request  # noqa: E402
from openad_service_utils.api.generation.call_generation_services import get_services as get_generation_services  # noqa: E402
from openad_service_utils.api.properties.call_property_services import service_requester as property_request
from openad_service_utils.api.properties.call_property_services import get_services as get_property_services
from pandas import DataFrame
from openad_service_utils.common.properties.property_factory import PropertyFactory
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import signal
import uvicorn
import sys
import gc
import os


app = FastAPI()
health_app = FastAPI()

gen_requester = generation_request()
prop_requester = property_request()


def clean_gpu_mem():
    try:
        import torch
        print(f"cleaning gpu memory for process ID: {os.getpid()}")
        torch.cuda.empty_cache()
    except ImportError:
        print("[I] cuda not available. skipping cleaning gpu memory job.")
    finally:
        gc.collect()


@health_app.get("/health", response_class=HTMLResponse)
async def healthz(request: Request):
    return "UP"


@app.get("/health", response_class=HTMLResponse)
async def health():
    return "UP"


@app.post("/service")
async def service(property_request: dict):
    # user request is for property prediction
    if property_request.get("service_type") in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
        result = prop_requester.route_service(property_request)
    # user request is for generation
    elif property_request.get("service_type") == "generate_data":
        result = gen_requester.route_service(property_request)
    else:
        return JSONResponse(
            {"message": "service not supported", "service_type": property_request.get("service_type")},
        )
    # cleanup resources before returning request
    clean_gpu_mem()
    if result is None:
        return JSONResponse(
            {"message": "could not process service request", "service": property_request.get("parameters",{}).get("property_type")},
        )
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


# Function to run the main service
def run_main_service(min_workers):
    uvicorn.run("openad_service_utils.api.server:app", host="0.0.0.0", port=8080, log_level="debug", workers=min_workers)


def run_health_service():
    uvicorn.run("openad_service_utils.api.server:health_app", host="0.0.0.0", port=8081, log_level="debug", workers=1)


def signal_handler(signum, frame, executor):
    print(f"Received signal {signum}, shutting down...")
    executor.shutdown(wait=True)
    sys.exit(0)


def start_server(host="0.0.0.0", port=8080, log_level="debug", min_workers=10, worker_gpu_min=2000):
    try:
        import torch
        if torch.cuda.is_available():
            print(f"\n[i] cuda is available: {torch.cuda.is_available()}")
            print(f"[i] cuda version: {torch.version.cuda}\n")
            print(f"[i] device name: {torch.cuda.get_device_name(0)}")
            print(f"[i] torch version: {torch.__version__}\n")
            # Get the current GPU device index
            gpu_id = torch.cuda.current_device()
            # Get the GPU properties
            gpu_properties = torch.cuda.get_device_properties(gpu_id)
            # Get the total GPU memory size in bytes
            total_memory = int(gpu_properties.total_memory / (1024 ** 2))
            # Calculate the max amount of workers for gpu size
            max_workers = total_memory // worker_gpu_min
            # TODO: increase min workers
            if max_workers < min_workers:
                # downsize the amount of workers if the gpu size is less than expected
                min_workers = max_workers
            print(f"Total GPU memory: {total_memory:.2f} MB")
            print(f"Total workers: {min_workers}")
    except ImportError:
        print("[i] cuda not available. Running on CPU only.")
        pass
    # process is run on linux. spawn.
    multiprocessing.set_start_method("spawn")
    with ProcessPoolExecutor() as executor:
        executor.submit(run_main_service, min_workers)
        executor.submit(run_health_service)
        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, executor))
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, executor))
        # Keep the main process running to handle signals and wait for child processes
        executor.shutdown(wait=True)


if __name__ == "__main__":
    start_server()
