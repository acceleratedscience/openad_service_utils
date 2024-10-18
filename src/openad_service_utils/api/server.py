import logging
import gc
import multiprocessing
import os
import signal
import sys
from concurrent.futures import ProcessPoolExecutor

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pandas import DataFrame
import copy

from openad_service_utils.api.generation.call_generation_services import \
    get_services as get_generation_services  # noqa: E402
from openad_service_utils.api.generation.call_generation_services import \
    service_requester as generation_request  # noqa: E402
from openad_service_utils.api.properties.call_property_services import \
    get_services as get_property_services
from openad_service_utils.api.properties.call_property_services import \
    service_requester as property_request
from openad_service_utils.common.properties.property_factory import \
    PropertyFactory
from openad_service_utils.utils.logging_config import setup_logging
from openad_service_utils.api.config import ServerConfig
import traceback
from itertools import chain

app = FastAPI()
kube_probe = FastAPI()

# Set up logging configuration
setup_logging()

# Create a logger
logger = logging.getLogger(__name__)

gen_requester = generation_request()
prop_requester = property_request()


def run_cleanup():
    if ServerConfig.AUTO_CLEAR_GPU_MEM:
        try:
            import torch
            logger.debug(f"cleaning gpu memory for process ID: {os.getpid()}")
            torch.cuda.empty_cache()
        except ImportError:
            pass  # do nothing
    if ServerConfig.AUTO_GARABAGE_COLLECT:
        logger.debug(f"manual garbage collection on process ID: {os.getpid()}")
        gc.collect()


@kube_probe.get("/health", response_class=HTMLResponse)
async def healthz(request: Request):
    return "UP"


@app.get("/health", response_class=HTMLResponse)
async def health():
    return "UP"


@app.post("/service")
async def service(property_request: dict):
    logger.info(f"Processing request {property_request}")
    original_request = copy.deepcopy(property_request)
    try:
        # user request is for property prediction
        if property_request.get("service_type") in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
            result = prop_requester.route_service(property_request)
        # user request is for generation
        elif property_request.get("service_type") == "generate_data":
            result = gen_requester.route_service(property_request)
        else:
            logger.error(f"Error processing request: {property_request}")
            raise HTTPException(status_code=500, detail={"error": "service mismatch", "input": original_request})
        # cleanup resources before returning request
        run_cleanup()
        if result is None:
            raise HTTPException(status_code=500, detail={"error": "service not found", "input": original_request})
        if isinstance(result, DataFrame):
            return result.to_dict(orient="records")
        else:
            return result
    except HTTPException as e:
        # reraise HTTPException to maintain the original status code and detail
        raise e
    except Exception as e:
        simple_error = f"{type(e).__name__}: {e}"
        logger.error(f"Error processing request: {simple_error}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail={"error": str(simple_error), "input": original_request})


@app.get("/service")
async def get_service_defs():
    """return service definitions"""
    logger.info("Retrieving service definitions")
    all_services = []
    # get generation service list
    gen_services: list = get_generation_services()
    if gen_services:
        all_services.extend(gen_services)
        logger.debug(f"generation models registered: {len(gen_services)}")
    # get property service list
    prop_services = get_property_services()
    if prop_services:
        all_services.extend(prop_services)
        logger.debug(f"property models registered: {len(prop_services)}")
    # check if services available
    if not all_services:
        logger.error("No property or generation services registered!")
    # log services
    try:
        logger.debug(f"Available types: {list(chain.from_iterable([i['valid_types'] for i in all_services]))}")
    except Exception as e:
        logger.warn(f"could not print types: {str(e)}")
    return JSONResponse(all_services)


# Function to run the main service
def run_main_service(host, port, log_level, max_workers):
    uvicorn.run("openad_service_utils.api.server:app", host=host, port=port, log_level=log_level, workers=max_workers)


def run_health_service(host, port, log_level, max_workers):
    uvicorn.run("openad_service_utils.api.server:kube_probe", host=host, port=port, log_level=log_level, workers=max_workers)


def signal_handler(signum, frame, executor):
    logger.debug(f"Received signal {signum}, shutting down...")
    executor.shutdown(wait=True)
    sys.exit(0)


def ignore_winch_signal(signum, frame):
    # ignore signal. do nothing
    return


def is_running_in_kubernetes():
    return "KUBERNETES_SERVICE_HOST" in os.environ


def start_server(host="0.0.0.0", port=8080, log_level="info", max_workers=1, worker_gpu_min=2000):
    try:
        import torch
        if torch.cuda.is_available():
            logger.debug(f"cuda is available: {torch.cuda.is_available()}")
            logger.debug(f"cuda version: {torch.version.cuda}")
            logger.debug(f"device name: {torch.cuda.get_device_name(0)}")
            logger.debug(f"torch version: {torch.__version__}")
            # Get the current GPU device index
            gpu_id = torch.cuda.current_device()
            # Get the GPU properties
            gpu_properties = torch.cuda.get_device_properties(gpu_id)
            # Get the total GPU memory size in bytes
            total_memory = int(gpu_properties.total_memory / (1024 ** 2))
            # Calculate the max amount of workers for gpu size
            available_workers = total_memory // worker_gpu_min
            # TODO: increase min workers
            if available_workers < max_workers:
                # downsize the amount of workers if the gpu size is less than expected
                max_workers = available_workers
                logger.warn("lowering amount of workers due to resource constraint")
            logger.debug(f"Total GPU memory: {total_memory:.2f} MB")
    except ImportError:
        logger.debug("cuda not available. Running on cpu.")
        pass
    if os.environ.get("GT4SD_S3_ACCESS_KEY", ""):
        logger.info(f"using private s3 model repository | Host: {os.environ.get('GT4SD_S3_HOST', '')}======")
    else:
        logger.info("using public gt4sd s3 model repository")
    logger.debug(f"Total workers: {max_workers}")
    # process is run on linux. spawn.
    multiprocessing.set_start_method("spawn")
    with ProcessPoolExecutor() as executor:
        executor.submit(run_main_service, host, port, log_level, max_workers)
        if is_running_in_kubernetes():
            logger.debug("Running in Kubernetes, starting health probe")
            executor.submit(run_health_service, host, port+1, log_level, 1)
        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, executor))
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, executor))
        signal.signal(signal.SIGWINCH, ignore_winch_signal)
        # Keep the main process running to handle signals and wait for child processes
        executor.shutdown(wait=True)


if __name__ == "__main__":
    start_server()
