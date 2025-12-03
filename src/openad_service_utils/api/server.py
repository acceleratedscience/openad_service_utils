# ----------------------------
# region --- Setup

# Std
import asyncio
import hashlib
import json
import logging
import multiprocessing
import os
import shutil
import signal
import sys
import time
from contextlib import asynccontextmanager
from itertools import chain
from pathlib import Path
from typing import List, Optional

# 3rd Party
import redis.asyncio as redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pandas import DataFrame
from starlette.background import BackgroundTask

# Core
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.api.generation.call_generation_services import (
    get_services as get_generation_services,
)
from openad_service_utils.api.generation.call_generation_services import (
    service_requester as generation_request,
)
from openad_service_utils.api.job_manager import (
    JobManager,
    clear_job_queues,
    retrieve_async_job,
    slave_thread,
)
from openad_service_utils.api.models import ServiceRequest, ServiceType
from openad_service_utils.api.properties.call_property_services import (
    get_services as get_property_services,
)
from openad_service_utils.api.properties.call_property_services import (
    service_requester as property_request,
)
from openad_service_utils.common.configuration import GT4SDConfiguration
from openad_service_utils.common.models import FileResponse as CustomFileResponse
from openad_service_utils.common.properties.property_factory import PropertyFactory

# Routers
from openad_service_utils.api.router_collections import collections_router, files_router_lifespan

# Utils
from openad_service_utils.utils.logging_config import setup_logging

# Set up logging configuration
setup_logging()

# Get the server configuration environment variables
settings = get_config_instance()

# Create a logger
logger = logging.getLogger(__name__)


# Dependency: Redis client
async def get_redis_client(request: Request) -> redis.Redis:
    return request.app.state.redis


# Dependency: Job Manager
async def get_job_manager(
    redis_client: redis.Redis = Depends(get_redis_client),
) -> JobManager:
    return JobManager(redis_client, "Master Queue")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init Redis connection pool
    app.state.redis = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
    )
    await clear_job_queues(app.state.redis)

    # Router files handle their own background tasks
    async with files_router_lifespan(app):
        yield

    # Close Redis connection
    await app.state.redis.close()
    logger.debug("Shutting down server...")


# Create FastAPI app with lifespan event
app = FastAPI(lifespan=lifespan)
kube_probe = FastAPI()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add optional routers for UI
app.include_router(collections_router)


@kube_probe.get("/health", response_class=HTMLResponse)
async def healthz(request: Request):
    return "UP"


@app.get("/", response_class=HTMLResponse)
@app.get("/health", response_class=HTMLResponse)
async def health():
    return "UP"


# Helper: generate a cache key
def generate_cache_key(request_data: dict) -> str:
    payload_str = json.dumps(request_data, sort_keys=True)
    return f"service_cache:{hashlib.sha256(payload_str.encode()).hexdigest()}"


# Ensure the upload temp directory exists
os.makedirs(settings.UPLOAD_STORAGE_DIR, exist_ok=True)  # <--  move to router?
os.makedirs(settings.ASYNC_JOB_PATH, exist_ok=True)


@app.post("/service")
async def service(
    restful_request: ServiceRequest, job_manager: JobManager = Depends(get_job_manager)
):
    # # @dummy test error
    # import random
    # if random.random() < 0.5:
    #     raise HTTPException(status_code=418, detail="This is a test.")

    original_request = restful_request.model_dump(by_alias=True)
    service_type = original_request.get("service_type")
    cache_key = generate_cache_key(original_request)

    # Return cached result if available (except for GET_RESULT)
    if settings.ENABLE_CACHE_RESULTS and service_type != ServiceType.GET_RESULT:
        cached = await app.state.redis.get(cache_key)
        if cached:
            return json.loads(cached)

    # Handle file_keys from the request
    file_keys_for_job = restful_request.file_keys if restful_request.file_keys else []

    # Validate file_keys
    if file_keys_for_job:
        for file_key in file_keys_for_job:
            if not await app.state.redis.exists(f"file_map:{file_key}"):
                raise HTTPException(
                    status_code=404, detail=f"File with key {file_key} not found."
                )

    try:
        if service_type == ServiceType.GET_RESULT:
            result = await retrieve_async_job(
                str(original_request.get("url")), app.state.redis
            )
            if result is None:
                return {"error": {"reason": "job does not exist"}}

        elif service_type in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
            result = await handle_job_submission(
                job_manager,
                property_request,
                original_request,
                file_keys=file_keys_for_job,
            )

        elif service_type == ServiceType.GENERATE_DATA:
            result = await handle_job_submission(
                job_manager,
                generation_request,
                original_request,
                file_keys=file_keys_for_job,
            )

        else:
            raise HTTPException(
                status_code=500,
                detail={"error": "service mismatch", "input": original_request},
            )

        if isinstance(result, CustomFileResponse) or (
            isinstance(result, dict) and "file_path" in result
        ):
            if isinstance(result, CustomFileResponse):
                file_path = result.file_path
                filename = os.path.basename(file_path)
            else:
                file_path = result["file_path"]
                filename = result.get("filename", os.path.basename(file_path))

            sandbox_dir = os.path.dirname(file_path)

            def cleanup():
                shutil.rmtree(sandbox_dir, ignore_errors=True)

            if os.path.exists(file_path):
                return FileResponse(
                    path=file_path,
                    media_type="application/octet-stream",
                    filename=filename,
                    background=BackgroundTask(cleanup),
                )
            else:
                cleanup()  # Clean up even if the file doesn't exist
                raise HTTPException(status_code=404, detail="File not found.")

        # Cache the result (except for GET_RESULT)
        if settings.ENABLE_CACHE_RESULTS and service_type != ServiceType.GET_RESULT:
            if isinstance(result, DataFrame):
                result = result.to_dict(orient="records")
            await app.state.redis.set(
                cache_key, json.dumps(result), ex=settings.REQUEST_CACHE_TTL
            )

        return result

    except HTTPException as e:
        logger.exception(e, exc_info=True)
        raise e
    except Exception as e:
        logger.error(f"Request: {original_request}")
        logger.exception(e, exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": str(e), "input": original_request}
        )
    # Cleanup of temporary files and Redis entries will be handled by the job_manager


async def handle_job_submission(
    job_manager: JobManager,
    request_obj,
    original_request,
    file_keys: Optional[List[str]] = None,
):
    submission_time = time.time()
    if settings.ASYNC_ALLOW and original_request.get("async"):
        job_id = await job_manager.submit_job(
            request_obj,
            "route_service",
            original_request,
            async_submission=True,
            file_keys=file_keys,
            submission_time=submission_time,
        )
        cache_key = generate_cache_key(original_request)
        await app.state.redis.set(
            cache_key, json.dumps(job_id), ex=settings.REQUEST_CACHE_TTL
        )
        return job_id
        # await app.state.redis.set(cache_key, json.dumps({"job_id": job_id}), ex=settings.REQUEST_CACHE_TTL)
        # return {"job_id": job_id}
    else:
        job_id = await job_manager.submit_job(
            request_obj,
            "route_service",
            original_request,
            file_keys=file_keys,
            submission_time=submission_time,
        )
        job_info = await job_manager.get_result_by_id(job_id)

        if job_info["status"] == "completed":
            return job_info["result"]
        else:
            error_detail = job_info.get("result", {}).get(
                "error", "Job failed without a specific error message."
            )
            raise HTTPException(
                status_code=500, detail={"error": error_detail, "job_id": job_id}
            )


@app.get("/service")
async def get_service_defs():
    """Return service definitions."""
    all_services = []

    # Get generation service list
    gen_services: list = get_generation_services()
    if gen_services:
        if settings.ASYNC_ALLOW:
            for _service in gen_services:
                _service["async_allow"] = settings.ASYNC_ALLOW
        all_services.extend(gen_services)
        logger.debug("generation models registered: %s", len(gen_services))

    # Get property service list
    prop_services = get_property_services()
    if settings.ASYNC_ALLOW:
        for _prop_service in prop_services:
            _prop_service["async_allow"] = settings.ASYNC_ALLOW
    if prop_services:
        all_services.extend(prop_services)
        logger.info("Available Property Services: %s", len(prop_services))

    # Check if services available
    if not all_services:
        logger.warning("No property or generation services registered!")

    # Log services
    try:
        logger.info(
            "Available Property types: %s",
            list(chain.from_iterable([i["valid_types"] for i in all_services])),
        )

    except Exception as e:  # pylint: disable=broad-except
        logger.warning("could not print types: %s", str(e))
    return JSONResponse(all_services)


def admin_endpoints_enabled():
    """Dependency to check if admin endpoints are enabled."""
    if not settings.ADMIN_ENDPOINTS_ENABLED:
        raise HTTPException(
            status_code=404,
            detail="Not Found",
        )


@app.get("/admin/details", dependencies=[Depends(admin_endpoints_enabled)])
def server_details():
    """return server details"""
    logger.info("Retrieving server details")
    return JSONResponse(settings.model_dump())


@app.get("/service/download/{job_id}/{filename}")
async def download_file(
    job_id: str, filename: str, job_manager: JobManager = Depends(get_job_manager)
):
    """
    Downloads the file result of a completed asynchronous job.
    """
    job_info = await job_manager._get_job_info_by_id(job_id)

    if not job_info:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not yet complete.")

    result = job_info.get("result")
    if (
        not isinstance(result, dict)
        or "file_path" not in result
        or not os.path.exists(result["file_path"])
    ):
        raise HTTPException(
            status_code=404, detail="Result file not found for this job."
        )

    file_path = result["file_path"]
    filename = result.get("filename", os.path.basename(file_path))

    # Security check: ensure the file is within the async path
    if not os.path.abspath(file_path).startswith(
        os.path.abspath(settings.ASYNC_JOB_PATH)
    ):
        raise HTTPException(status_code=403, detail="Access to this file is forbidden.")

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=filename,
    )


# Function to run the main service
def run_main_service(host, port, log_level, workers):
    uvicorn.run(
        "openad_service_utils.api.server:app",
        host=host,
        port=port,
        log_level=log_level,
        workers=workers,
        reload=True,
    )


def run_health_service(host, port, log_level, workers):
    uvicorn.run(
        "openad_service_utils.api.server:kube_probe",
        host=host,
        port=port,
        log_level=log_level,
        workers=workers,
    )


def signal_handler(signum, frame, processes):
    logger.debug(f"Received signal {signum}, shutting down...")
    for p in processes:
        p.terminate()
        p.join()
    logger.debug("All processes terminated.")
    sys.exit(0)


def ignore_winch_signal(signum, frame):
    # ignore signal. do nothing
    return


def is_running_in_kubernetes():
    return "KUBERNETES_SERVICE_HOST" in os.environ


def start_server(
    host=settings.HOST,
    port=settings.PORT,
    log_level=settings.UVICORN_LOG_LEVEL,
    max_workers=settings.SERVE_MAX_WORKERS,
    worker_gpu_min=settings.SERVE_WORKER_GPU_MIN,
):
    """
    Starts the FastAPI server with configurable options.

    Args:
        host (str): The host to bind the server to.
        port (int): The port to run the server on.
        log_level (str): The logging level for Uvicorn.
        max_workers (int): The maximum number of worker processes.
        worker_gpu_min (int): The minimum GPU memory required per worker.
    """
    logger.debug(f"Server Config: {settings.model_dump()}")
    # Track main process
    os.environ["OPENAD_MAIN_PROCESS"] = "1"

    try:
        import torch

        if torch.cuda.is_available():
            logger.debug(f"CUDA is available: {torch.cuda.is_available()}")
            logger.debug(f"CUDA version: {torch.version.cuda}")  # type: ignore # noqa: F821
            logger.debug(f"Device name: {torch.cuda.get_device_name(0)}")
            logger.debug(f"Torch version: {torch.__version__}")
            gpu_id = torch.cuda.current_device()
            gpu_properties = torch.cuda.get_device_properties(gpu_id)
            total_memory = int(gpu_properties.total_memory / (1024**2))
            available_workers = total_memory // worker_gpu_min
            if available_workers < max_workers:
                max_workers = available_workers
                logger.warning("Lowering amount of workers due to resource constraint.")
            logger.debug(f"Total GPU memory: {total_memory:.2f} MB")
    except ImportError:
        logger.debug("CUDA not available. Running on CPU.")

    if os.environ.get("GT4SD_S3_ACCESS_KEY", ""):
        logger.info(
            f"Using private S3 model repository | Host: {os.environ.get('GT4SD_S3_HOST', '')}"
        )
    else:
        logger.info("Using public GT4SD S3 model repository.")

    config_settings = GT4SDConfiguration().model_dump(
        include={"OPENAD_S3_HOST", "OPENAD_S3_HOST_HUB"}
    )
    logger.info(f"S3 Config: {config_settings}")
    # logger.info(f"Total workers: {max_workers}")

    multiprocessing.set_start_method("spawn", force=True)

    processes = []
    try:
        # Start job worker pool
        for i in range(settings.WORKER_COUNT):
            worker_process = multiprocessing.Process(target=slave_thread, args=(i + 1,))
            processes.append(worker_process)
            worker_process.start()
            logger.info(f"Started worker process {i+1} with PID: {worker_process.pid}")

        # Start Uvicorn main service
        main_service_process = multiprocessing.Process(
            target=run_main_service, args=(host, port, log_level, 1)
        )
        processes.append(main_service_process)
        main_service_process.start()
        logger.info(
            f"Uvicorn main service started on {host}:{port} with PID: {main_service_process.pid}"
        )

        # Start Kubernetes health probe if in Kubernetes
        if is_running_in_kubernetes():
            health_service_process = multiprocessing.Process(
                target=run_health_service,
                args=(host, settings.PROBE_PORT, log_level, 1),
            )
            processes.append(health_service_process)
            health_service_process.start()
            logger.info(
                f"Kubernetes health probe started on {host}:{settings.PROBE_PORT}."
            )

        # Set up signal handling
        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, processes))
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, processes))
        signal.signal(signal.SIGWINCH, ignore_winch_signal)

        # Wait for all processes to complete
        for p in processes:
            p.join()

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logger.info("Shutting down server.")
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join()
        if "OPENAD_MAIN_PROCESS" in os.environ:
            del os.environ["OPENAD_MAIN_PROCESS"]


# endregion
# ----------------------------


if __name__ == "__main__":
    start_server()
