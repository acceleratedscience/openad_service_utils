import asyncio
import hashlib
import json
import logging
import multiprocessing
import os
import re
import shutil
import signal
import time
import sys
from contextlib import asynccontextmanager
from itertools import chain
from typing import List, Optional

import redis.asyncio as redis
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pandas import DataFrame
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from openad_service_utils.common.models import FileResponse as CustomFileResponse

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
from openad_service_utils.common.properties.property_factory import PropertyFactory
from openad_service_utils.utils.logging_config import setup_logging

# Set up logging configuration
setup_logging()

# Get the server configuration environment variables
settings = get_config_instance()

# Create a logger
logger = logging.getLogger(__name__)


async def get_redis(request: Request) -> redis.Redis:
    return request.app.state.redis


# create lifecycle event to initialize the job manager
async def get_job_manager(redis_client: redis.Redis = Depends(get_redis)) -> JobManager:
    return JobManager(redis_client, "Master Queue")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init Redis connection pool
    app.state.redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD, decode_responses=True)
    await clear_job_queues(app.state.redis)
    
    # Start the file sync background task
    task = asyncio.create_task(sync_files_periodically(app.state.redis))
    
    yield
    
    task.cancel()
    await app.state.redis.close()

    logger.debug("Shutting down server...")
    # Cleanup code here


# Create FastAPI app with lifespan event
app = FastAPI(lifespan=lifespan)
kube_probe = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Ensure the upload temp directory exists
os.makedirs(settings.UPLOAD_STORAGE_DIR, exist_ok=True)


def validate_collection_name(collection_name: str):
    """Validates the collection name to be alphanumeric with underscores and hyphens."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", collection_name):
        raise HTTPException(status_code=400, detail="Invalid collection name. Only alphanumeric characters, underscores, and hyphens are allowed.")


def validate_filename(filename: str):
    """Validates the filename to prevent directory traversal."""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")


async def sync_files_to_redis(redis_client: redis.Redis):
    """Scans the upload directory and syncs the file index with Redis."""
    # logger.debug("Starting file sync to Redis.")
    
    # Get all file keys from Redis
    redis_keys = [key async for key in redis_client.scan_iter("file_map:*")]
    redis_file_keys = {key.split(":")[1] for key in redis_keys}

    # Get all files from the filesystem, assuming subdirectories are collections
    disk_files = set()
    for collection_name in os.listdir(settings.UPLOAD_STORAGE_DIR):
        collection_path = os.path.join(settings.UPLOAD_STORAGE_DIR, collection_name)
        if os.path.isdir(collection_path):
            try:
                validate_collection_name(collection_name)
                for filename in os.listdir(collection_path):
                    full_path = os.path.join(collection_path, filename)
                    if os.path.isfile(full_path):
                        try:
                            validate_filename(filename)
                            file_key = os.path.join(collection_name, filename)
                            disk_files.add(file_key)
                        except HTTPException:
                            logger.warning(f"Skipping invalid filename during sync: {filename}")
            except HTTPException:
                logger.warning(f"Skipping invalid collection name during sync: {collection_name}")

    # Add new files to Redis
    new_files = disk_files - redis_file_keys
    for file_key in new_files:
        full_path = os.path.join(settings.UPLOAD_STORAGE_DIR, file_key)
        await redis_client.set(f"file_map:{file_key}", full_path)
        logger.debug(f"Added new file to Redis: {file_key}")

    # Remove deleted files from Redis
    deleted_files = redis_file_keys - disk_files
    if deleted_files:
        await redis_client.delete(*[f"file_map:{key}" for key in deleted_files])
        logger.debug(f"Removed deleted files from Redis: {deleted_files}")


async def sync_files_periodically(redis_client: redis.Redis):
    """Runs the file sync process at a regular interval."""
    logger.info("Starting background file sync task...")
    while True:
        await sync_files_to_redis(redis_client)
        await asyncio.sleep(settings.UPLOAD_STORAGE_SYNC_INTERVAL)  # Sync every 60 seconds


@app.post("/service/collections/{collection_name}")
async def upload_file_to_collection(collection_name: str, file: UploadFile = File(...)):
    """Uploads a file to a specific collection."""
    validate_collection_name(collection_name)
    try:
        filename = file.filename if file.filename else "uploaded_file"
        validate_filename(filename)
        collection_dir = os.path.join(settings.UPLOAD_STORAGE_DIR, collection_name)
        os.makedirs(collection_dir, exist_ok=True)
        
        file_path = os.path.join(collection_dir, filename)
        # Offload blocking file write to a thread pool
        await run_in_threadpool(shutil.copyfileobj, file.file, open(file_path, "wb"))
        
        file_key = os.path.join(collection_name, filename)
        await app.state.redis.set(f"file_map:{file_key}", file_path)
        
        return JSONResponse({"file_key": file_key, "message": "File uploaded successfully."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.get("/service/collections")
async def get_collections():
    """Returns a list of all available collections."""
    try:
        file_keys = [key async for key in app.state.redis.scan_iter("file_map:*")]
        collections = sorted(list(set([key.split(":")[1].split("/")[0] for key in file_keys])))
        return JSONResponse({"collections": collections})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving collections: {str(e)}")


@app.delete("/service/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Deletes an entire collection and all of its files."""
    validate_collection_name(collection_name)
    try:
        collection_dir = os.path.join(settings.UPLOAD_STORAGE_DIR, collection_name)
        if not os.path.isdir(collection_dir):
            raise HTTPException(status_code=404, detail="Collection not found.")

        # Remove all files in the collection from Redis
        file_keys = [key async for key in app.state.redis.scan_iter(f"file_map:{collection_name}/*")]
        if file_keys:
            await app.state.redis.delete(*file_keys)

        # Remove the collection directory from the filesystem
        shutil.rmtree(collection_dir)

        return JSONResponse({"message": f"Collection '{collection_name}' deleted successfully."})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")


@app.get("/service/collections/{collection_name}")
async def get_files_in_collection(collection_name: str):
    """Returns a list of all files in a specific collection."""
    validate_collection_name(collection_name)
    try:
        files_info = []
        file_keys = [key async for key in app.state.redis.scan_iter(f"file_map:{collection_name}/*")]

        # Handle case where collection directory might exist but be empty
        if not file_keys:
            collection_dir = os.path.join(settings.UPLOAD_STORAGE_DIR, collection_name)
            # Use threadpool for blocking I/O
            if not await run_in_threadpool(os.path.isdir, collection_dir):
                raise HTTPException(status_code=404, detail="Collection not found.")
            # If the directory exists but is empty, return an empty list
            return JSONResponse({"files": []})

        for key in sorted(file_keys):
            file_key = key.split(":")[1]
            filename = os.path.basename(file_key)
            file_path = await app.state.redis.get(key)
            file_size = 0
            if file_path and await run_in_threadpool(os.path.exists, file_path):
                file_size = await run_in_threadpool(os.path.getsize, file_path)
            files_info.append({"file_key": file_key, "filename": filename, "size_bytes": file_size})
        return JSONResponse({"files": files_info})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving files: {str(e)}")


@app.get("/service/collections/{collection_name}/{filename}")
async def download_file_from_collection(collection_name: str, filename: str):
    """Downloads a file from a specific collection."""
    validate_collection_name(collection_name)
    validate_filename(filename)
    try:
        file_key = os.path.join(collection_name, filename)
        file_path = await app.state.redis.get(f"file_map:{file_key}")

        if not file_path or not await run_in_threadpool(os.path.exists, file_path):
            raise HTTPException(status_code=404, detail="File not found.")

        # Security check: ensure the file is within the upload storage directory
        if not os.path.abspath(file_path).startswith(os.path.abspath(settings.UPLOAD_STORAGE_DIR)):
            raise HTTPException(status_code=403, detail="Access to this file is forbidden.")

        return FileResponse(
            path=file_path,
            media_type="application/octet-stream",
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


@app.delete("/service/collections/{collection_name}/{filename}")
async def delete_file_from_collection(collection_name: str, filename: str):
    """Deletes a file from a specific collection."""
    validate_collection_name(collection_name)
    validate_filename(filename)
    try:
        file_key = os.path.join(collection_name, filename)
        file_path = await app.state.redis.get(f"file_map:{file_key}")

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found.")
            
        os.remove(file_path)
        await app.state.redis.delete(f"file_map:{file_key}")
        
        return JSONResponse({"message": "File deleted successfully."})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


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

    # Handle file_keys from the request
    file_keys_for_job = restful_request.file_keys if restful_request.file_keys else []

    # Validate file_keys
    if file_keys_for_job:
        for file_key in file_keys_for_job:
            if not await app.state.redis.exists(f"file_map:{file_key}"):
                raise HTTPException(status_code=404, detail=f"File with key {file_key} not found.")

    try:
        if service_type == ServiceType.GET_RESULT:
            result = await retrieve_async_job(str(original_request.get("url")), app.state.redis)
            if result is None:
                return {"error": {"reason": "job does not exist"}}

        elif service_type in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
            result = await handle_job_submission(
                job_manager, property_request, original_request, file_keys=file_keys_for_job
            )

        elif service_type == ServiceType.GENERATE_DATA:
            result = await handle_job_submission(
                job_manager, generation_request, original_request, file_keys=file_keys_for_job
            )

        else:
            raise HTTPException(status_code=500, detail={"error": "service mismatch", "input": original_request})

        if isinstance(result, CustomFileResponse) or (isinstance(result, dict) and "file_path" in result):
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
            await app.state.redis.set(cache_key, json.dumps(result), ex=settings.REQUEST_CACHE_TTL)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e), "input": original_request})
    # Cleanup of temporary files and Redis entries will be handled by the job_manager


async def handle_job_submission(
    job_manager: JobManager, request_obj, original_request, file_keys: Optional[List[str]] = None
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
        await app.state.redis.set(cache_key, json.dumps(job_id), ex=settings.REQUEST_CACHE_TTL)
        return job_id
        # await app.state.redis.set(cache_key, json.dumps({"job_id": job_id}), ex=settings.REQUEST_CACHE_TTL)
        # return {"job_id": job_id}
    else:
        job_id = await job_manager.submit_job(
            request_obj, "route_service", original_request, file_keys=file_keys, submission_time=submission_time
        )
        job_info = await job_manager.get_result_by_id(job_id)
        
        if job_info["status"] == "completed":
            return job_info["result"]
        else:
            error_detail = job_info.get("result", {}).get("error", "Job failed without a specific error message.")
            raise HTTPException(status_code=500, detail={"error": error_detail, "job_id": job_id})


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


@app.get("/service/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str, job_manager: JobManager = Depends(get_job_manager)):
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
        raise HTTPException(status_code=404, detail="Result file not found for this job.")

    file_path = result["file_path"]
    filename = result.get("filename", os.path.basename(file_path))

    # Security check: ensure the file is within the async path
    if not os.path.abspath(file_path).startswith(os.path.abspath(settings.ASYNC_JOB_PATH)):
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
            logger.debug(f"CUDA version: {torch.version.cuda}") # type: ignore # noqa: F821
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
        logger.info(f"Using private S3 model repository | Host: {os.environ.get('GT4SD_S3_HOST', '')}")
    else:
        logger.info("Using public GT4SD S3 model repository.")

    config_settings = GT4SDConfiguration().model_dump(include={"OPENAD_S3_HOST", "OPENAD_S3_HOST_HUB"})
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
        logger.info(f"Uvicorn main service started on {host}:{port} with PID: {main_service_process.pid}")

        # Start Kubernetes health probe if in Kubernetes
        if is_running_in_kubernetes():
            health_service_process = multiprocessing.Process(
                target=run_health_service, args=(host, settings.PROBE_PORT, log_level, 1)
            )
            processes.append(health_service_process)
            health_service_process.start()
            logger.info(f"Kubernetes health probe started on {host}:{settings.PROBE_PORT}.")

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
        


if __name__ == "__main__":
    start_server()
