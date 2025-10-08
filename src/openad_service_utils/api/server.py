import asyncio
import gc
import hashlib
import json
import logging
import multiprocessing
import os
import re
import shutil
import signal
import sys
import uuid
from concurrent.futures import ProcessPoolExecutor
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
    delete_sync_submission_queue,
    get_job_manager,
    get_slaves,
    retrieve_async_job,
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
SLAVES = None


# create lifecycle event to initialize the job manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init Redis connection pool
    app.state.redis = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD, decode_responses=True)
    await delete_sync_submission_queue()
    
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


def run_cleanup():
    if settings.AUTO_CLEAR_GPU_MEM:
        try:
            import torch # type: ignore # noqa: F401, I001

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


# Ensure the upload temp directory exists
os.makedirs(settings.UPLOAD_TEMP_DIR, exist_ok=True)


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
    logger.debug("Starting file sync to Redis.")
    
    # Get all file keys from Redis
    redis_keys = await redis_client.keys("file_map:*")
    redis_file_keys = {key.split(":", 1)[1] for key in redis_keys}

    # Get all files from the filesystem, assuming subdirectories are collections
    disk_files = set()
    for collection_name in os.listdir(settings.UPLOAD_TEMP_DIR):
        collection_path = os.path.join(settings.UPLOAD_TEMP_DIR, collection_name)
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
    for file_key in disk_files - redis_file_keys:
        full_path = os.path.join(settings.UPLOAD_TEMP_DIR, file_key)
        await redis_client.set(f"file_map:{file_key}", full_path)
        logger.debug(f"Added new file to Redis: {file_key}")

    # Remove deleted files from Redis
    for file_key in redis_file_keys - disk_files:
        await redis_client.delete(f"file_map:{file_key}")
        logger.debug(f"Removed deleted file from Redis: {file_key}")

    logger.debug("File sync to Redis complete.")


async def sync_files_periodically(redis_client: redis.Redis):
    """Runs the file sync process at a regular interval."""
    while True:
        await sync_files_to_redis(redis_client)
        await asyncio.sleep(60)  # Sync every 60 seconds


@app.post("/service/collections/{collection_name}")
async def upload_file_to_collection(collection_name: str, file: UploadFile = File(...)):
    """Uploads a file to a specific collection."""
    validate_collection_name(collection_name)
    try:
        filename = file.filename if file.filename else "uploaded_file"
        validate_filename(filename)
        collection_dir = os.path.join(settings.UPLOAD_TEMP_DIR, collection_name)
        os.makedirs(collection_dir, exist_ok=True)
        
        file_path = os.path.join(collection_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_key = os.path.join(collection_name, filename)
        await app.state.redis.set(f"file_map:{file_key}", file_path)
        
        return JSONResponse({"file_key": file_key, "message": "File uploaded successfully."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@app.get("/service/collections")
async def get_collections():
    """Returns a list of all available collections."""
    try:
        file_keys = await app.state.redis.keys("file_map:*")
        collections = sorted(list(set([key.split(":")[1].split("/")[0] for key in file_keys])))
        return JSONResponse({"collections": collections})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving collections: {str(e)}")


@app.delete("/service/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Deletes an entire collection and all of its files."""
    validate_collection_name(collection_name)
    try:
        collection_dir = os.path.join(settings.UPLOAD_TEMP_DIR, collection_name)
        if not os.path.isdir(collection_dir):
            raise HTTPException(status_code=404, detail="Collection not found.")

        # Remove all files in the collection from Redis
        file_keys = await app.state.redis.keys(f"file_map:{collection_name}/*")
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
        file_keys = await app.state.redis.keys(f"file_map:{collection_name}/*")
        if not file_keys:
            raise HTTPException(status_code=404, detail="Collection not found or is empty.")
        for key in file_keys:
            file_key = key.split(":")[1]
            filename = os.path.basename(file_key)
            files_info.append({"file_key": file_key, "filename": filename})
        return JSONResponse({"files": files_info})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving files: {str(e)}")


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
            result = await retrieve_async_job(original_request.get("url"))
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

        if isinstance(result, CustomFileResponse):
            file_path = result.file_path
            sandbox_dir = os.path.dirname(file_path)

            def cleanup():
                shutil.rmtree(sandbox_dir, ignore_errors=True)

            if os.path.exists(file_path):
                return FileResponse(
                    path=file_path,
                    media_type="application/octet-stream",
                    filename=os.path.basename(file_path),
                    background=BackgroundTask(cleanup),
                )
            else:
                cleanup()  # Clean up even if the file doesn't exist
                raise HTTPException(status_code=404, detail="File not found.")

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
    # Cleanup of temporary files and Redis entries will be handled by the job_manager


async def handle_job_submission(job_manager: JobManager, request_obj, original_request, file_keys: Optional[List[str]] = None):
    if settings.ASYNC_ALLOW and original_request.get("async"):
        job_id = await job_manager.submit_job(request_obj, "route_service_async", original_request, async_submission=True, file_keys=file_keys)
        cache_key = generate_cache_key(original_request)
        await app.state.redis.set(cache_key, json.dumps(job_id), ex=settings.CACHE_TTL)
        return job_id
    else:
        job_id = await job_manager.submit_job(request_obj, "route_service", original_request, file_keys=file_keys)
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


@app.get("/service/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    """
    Downloads the file result of a completed asynchronous job.
    """
    job_manager = await get_job_manager()
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


def start_server(
    host="0.0.0.0",
    port=8080,
    log_level="info",
    max_workers=1,
    worker_gpu_min=2000,
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

    # Assuming JobManager is in the same file or imported correctly

    if settings.SERVE_MAX_WORKERS > 0:
        # overwite max workers with env var
        max_workers = settings.SERVE_MAX_WORKERS
    try:
        import torch # type: ignore # noqa: F401, I001

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
