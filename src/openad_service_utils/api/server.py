import logging
import gc
import asyncio
import redis.asyncio as redis
import hashlib
import json
import multiprocessing
import os
import signal
import sys
from concurrent.futures import ProcessPoolExecutor
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Depends
from pandas import DataFrame
from openad_service_utils.api.models import ServiceRequest, ServiceType
from openad_service_utils.api.job_manager import (
    JobManager,
    get_slaves,
    get_job_manager,
    delete_sync_submission_queue,
    retrieve_async_job,
)
from starlette.responses import JSONResponse
import copy

from openad_service_utils.api.generation.call_generation_services import (
    get_services as get_generation_services,
)  # noqa: E402
from openad_service_utils.api.generation.call_generation_services import (
    service_requester as generation_request,
)  # noqa: E402
from openad_service_utils.api.properties.call_property_services import (
    get_services as get_property_services,
)
from openad_service_utils.api.properties.call_property_services import (
    service_requester as property_request,
)
from openad_service_utils.common.properties.property_factory import PropertyFactory
from openad_service_utils.utils.logging_config import setup_logging
from openad_service_utils.api.config import get_config_instance
import traceback
from itertools import chain
from openad_service_utils.utils.convert import dict_to_json_string

from openad_service_utils.common.configuration import GT4SDConfiguration
import pandas as pd
from contextlib import asynccontextmanager


# Set up logging configuration
setup_logging()

# Get the server configuration environment variables
settings = get_config_instance()

# Create a logger
logger = logging.getLogger(__name__)
SLAVES = None


# create lifecycle event to initialize the job manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init Redis connection pool
    app.state.redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD, decode_responses=True)
    await delete_sync_submission_queue()
    yield
    await app.state.redis.close()

    logger.debug("Shutting down server...")
    # Cleanup code here


# Create FastAPI app with lifespan event
app = FastAPI(lifespan=lifespan)
kube_probe = FastAPI()


def run_cleanup():
    if settings.AUTO_CLEAR_GPU_MEM:
        try:
            import torch

            logger.debug(f"cleaning gpu memory for process ID: {os.getpid()}")
            torch.cuda.empty_cache()
        except ImportError:
            pass  # do nothing
    if settings.AUTO_GARBAGE_COLLECT:
        logger.debug(f"manual garbage collection on process ID: {os.getpid()}")
        gc.collect()


@kube_probe.get("/health", response_class=HTMLResponse)
async def healthz(request: Request):
    return "UP"


@app.get("/health", response_class=HTMLResponse)
async def health():
    return "UP"


# Helper: generate a cache key
def generate_cache_key(request_data: dict) -> str:
    payload_str = json.dumps(request_data, sort_keys=True)
    return f"service_cache:{hashlib.sha256(payload_str.encode()).hexdigest()}"


@app.post("/service")
async def service(
    restful_request: ServiceRequest,
    job_manager: JobManager = Depends(get_job_manager)
):
    original_request = restful_request.model_dump(by_alias=True)
    service_type = original_request.get("service_type")
    cache_key = generate_cache_key(original_request)

    # Return cached result if available (except for GET_RESULT)
    if settings.ENABLE_CACHE_RESULTS and service_type != ServiceType.GET_RESULT:
        cached = await app.state.redis.get(cache_key)
        if cached:
            return json.loads(cached)

    try:
        if service_type == ServiceType.GET_RESULT:
            result = await retrieve_async_job(original_request.get("url"))
            if result is None:
                return {"error": {"reason": "job does not exist"}}

        elif service_type in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
            result = await handle_job_submission(
                job_manager, property_request, original_request
            )

        elif service_type == ServiceType.GENERATE_DATA:
            result = await handle_job_submission(
                job_manager, generation_request, original_request
            )

        else:
            raise HTTPException(status_code=500, detail={"error": "service mismatch", "input": original_request})

        # Cache the result (except for GET_RESULT)
        if settings.ENABLE_CACHE_RESULTS and service_type != ServiceType.GET_RESULT:
            if isinstance(result, DataFrame):
                result = result.to_dict(orient="records")
            await app.state.redis.set(cache_key, json.dumps(result), ex=settings.CACHE_TTL)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e), "input": original_request})


async def handle_job_submission(job_manager, request_obj, original_request):
    if settings.ASYNC_ALLOW and original_request.get("async"):
        job_id = await job_manager.submit_job(request_obj, "route_service_async", original_request, async_submission=True)
        cache_key = generate_cache_key(original_request)
        await app.state.redis.set(cache_key, json.dumps(job_id), ex=settings.CACHE_TTL)
        return job_id
    else:
        job_id = await job_manager.submit_job(request_obj, "route_service", original_request)
        all_result = await job_manager.get_result_by_id(job_id)
        return all_result["result"]


@app.get("/service")
async def get_service_defs():
    """return service definitions"""
    all_services = []
    # get generation service list
    gen_services: list = get_generation_services()
    if gen_services:
        if settings.ASYNC_ALLOW:
            for i in range(len(gen_services)):
                gen_services[i]["async_allow"] = settings.ASYNC_ALLOW
        all_services.extend(gen_services)
        logger.debug(f"generation models registered: {len(gen_services)}")
    # get property service list
    prop_services = get_property_services()
    if settings.ASYNC_ALLOW:
        for i in range(len(prop_services)):
            prop_services[i]["async_allow"] = settings.ASYNC_ALLOW
    if prop_services:
        all_services.extend(prop_services)
        logger.info(f"Available Property Services: {len(prop_services)}")
    # check if services available
    if not all_services:
        logger.warning("No property or generation services registered!")
    # log services
    try:
        logger.info(f"Available Property types: {list(chain.from_iterable([i['valid_types'] for i in all_services]))}")
    except Exception as e:
        logger.warning(f"could not print types: {str(e)}")
    return JSONResponse(all_services)


@app.get("/admin/details")
def server_details():
    """return server details"""
    logger.info("Retrieving server details")
    return JSONResponse(settings.model_dump())


# Function to run the main service
def run_main_service(host, port, log_level, max_workers):
    uvicorn.run(
        "openad_service_utils.api.server:app",
        host=host,
        port=port,
        log_level=log_level,
        workers=max_workers,
    )


def run_health_service(host, port, log_level, max_workers):
    uvicorn.run(
        "openad_service_utils.api.server:kube_probe",
        host=host,
        port=port,
        log_level=log_level,
        workers=max_workers,
    )


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
    logger.debug(f"Server Config: {settings.model_dump()}")

    # Assuming JobManager is in the same file or imported correctly

    if settings.SERVE_MAX_WORKERS > 0:
        # overwite max workers with env var
        max_workers = settings.SERVE_MAX_WORKERS
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
            total_memory = int(gpu_properties.total_memory / (1024**2))
            # Calculate the max amount of workers for gpu size
            available_workers = total_memory // worker_gpu_min
            # TODO: increase min workers
            if available_workers < max_workers:
                # downsize the amount of workers if the gpu size is less than expected
                max_workers = available_workers
                logger.warning("lowering amount of workers due to resource constraint")
            logger.debug(f"Total GPU memory: {total_memory:.2f} MB")
    except ImportError:
        logger.debug("cuda not available. Running on cpu.")
        pass

    if os.environ.get("GT4SD_S3_ACCESS_KEY", ""):
        logger.info(f"using private s3 model repository | Host: {os.environ.get('GT4SD_S3_HOST', '')}======")
    else:
        logger.info("using public gt4sd s3 model repository")

    config_settings = GT4SDConfiguration().model_dump(include={"OPENAD_S3_HOST", "OPENAD_S3_HOST_HUB"})
    logger.info(f"S3 Config: {config_settings}")

    logger.debug(f"Total workers: {max_workers}")
    # process is run on linux. spawn.
    multiprocessing.set_start_method("spawn", force=True)
    global SLAVES

    with ProcessPoolExecutor() as executor:
        executor.submit(run_main_service, host, port, log_level, max_workers)
        if is_running_in_kubernetes():
            logger.debug("Running in Kubernetes, starting health probe")
            executor.submit(run_health_service, host, port + 1, log_level, 1)
        if SLAVES is None:
            SLAVES = asyncio.run(get_slaves())

        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, executor))
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, executor))
        signal.signal(signal.SIGWINCH, ignore_winch_signal)
        # Keep the main process running to handle signals and wait for child processes
        executor.shutdown(wait=True)


if __name__ == "__main__":
    start_server()
