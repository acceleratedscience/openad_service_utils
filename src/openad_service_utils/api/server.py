import logging
import gc
import multiprocessing
import os
import signal
import sys
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, Optional, List, Union

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Query, Path, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pandas import DataFrame
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
from openad_service_utils.api.async_call import background_route_service, retrieve_job
from openad_service_utils.common.configuration import GT4SDConfiguration

# Import the new asynchronous inference system
from openad_service_utils.common.async_utils.config import (
    AsyncInferenceConfig, get_default_config, get_config_from_env
)
from openad_service_utils.common.async_utils.service_adapters import (
    get_property_adapter, get_generation_adapter, shutdown_adapters
)
from openad_service_utils.common.async_utils.request_queue import RequestPriority

app = FastAPI(
    title="OpenAD Service API",
    description="API for OpenAD model inference services with asynchronous request handling",
    version="2.0.0",
)
kube_probe = FastAPI()

# Set up logging configuration
setup_logging()

# Create a logger
logger = logging.getLogger(__name__)

# Initialize the service requesters
gen_requester = generation_request()
prop_requester = property_request()

# Initialize the async service adapters
async_config = get_config_from_env()
property_adapter = get_property_adapter(prop_requester, async_config)
generation_adapter = get_generation_adapter(gen_requester, async_config)

# Check if async is allowed
try:
    ASYNC_ALLOW = os.environ.get("ASYNC_ALLOW", "false").lower() in ("true", "1", "yes")
except:
    ASYNC_ALLOW = False

logger.info(f"Async processing is {'enabled' if ASYNC_ALLOW else 'disabled'}")


def run_cleanup():
    if get_config_instance().AUTO_CLEAR_GPU_MEM:
        try:
            import torch

            logger.debug(f"cleaning gpu memory for process ID: {os.getpid()}")
            torch.cuda.empty_cache()
        except ImportError:
            pass  # do nothing
    if get_config_instance().AUTO_GARABAGE_COLLECT:
        logger.debug(f"manual garbage collection on process ID: {os.getpid()}")
        gc.collect()


@kube_probe.get("/health", response_class=HTMLResponse)
async def healthz(request: Request):
    return "UP"


@app.get("/health", response_class=HTMLResponse)
async def health():
    return "UP"


@app.post("/service", summary="Process a service request")
async def service(restful_request: dict):
    """
    Process a service request for property prediction or data generation.
    
    If the request has "async": true and async processing is enabled, the request
    will be processed asynchronously and a request ID will be returned.
    """
    logger.info(f"Processing request {restful_request}")
    original_request = copy.deepcopy(restful_request)
    if get_config_instance().ENABLE_CACHE_RESULTS:
        # convert input to string for caching
        restful_request = dict_to_json_string(restful_request)

    try:
        # Check if this is a request to get a result
        if original_request.get("service_type") == "get_result":
            # First try the new async system
            request_id = original_request.get("request_id")
            if request_id:
                # Try to get the result from the property adapter first
                logger.warning(f"Checking request status for {request_id}")
                result = property_adapter.get_request_status(request_id)
                if result and "error" not in result:
                    return result
                
                # If not found, try the generation adapter
                result = generation_adapter.get_request_status(request_id)
                if result and "error" not in result:
                    return result
                
                # If not found in either adapter, return an error
                return {"error": {"reason": "job does not exist"}}
            
            # Fall back to the old system if no request_id
            url = original_request.get("url")
            if url:
                result = retrieve_job(url)
                if result is None:
                    return {"error": {"reason": "job does not exist"}}
                return result
            
            # No request_id or url provided
            return {"error": {"reason": "no request_id or url provided"}}
            
        # Check if this is a property prediction request
        elif original_request.get("service_type") in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
            # Check if async processing is requested and allowed
            logger.warning(f"Processing property request: {original_request.get('async')}")
            if ASYNC_ALLOW and original_request.get("async", False):
                logger.warning(f"Processing property request asynchronously")
                # Use the new async system
                if original_request.get("use_enhanced_async", False):
                    logger.warning(f"Using enhanced async system")
                    # Get priority if specified
                    priority = original_request.get("priority", "normal")
                    timeout = original_request.get("timeout_seconds")
                    
                    # Submit the request to the async system
                    result = property_adapter.submit_async_request(
                        request_data=restful_request,
                        priority=priority,
                        timeout_seconds=timeout
                    )
                    return result
                else:
                    logger.warning(f"Using legacy async system")
                    # Use the legacy async system
                    result = background_route_service(prop_requester, restful_request)
            else:
                logger.warning(f"Processing property request synchronously")
                # Process synchronously
                result = prop_requester.route_service(restful_request)
                
        # Check if this is a generation request
        elif original_request.get("service_type") == "generate_data":
            # Check if async processing is requested and allowed
            if ASYNC_ALLOW and original_request.get("async", False):
                # Use the new async system
                if original_request.get("use_enhanced_async", False):
                    # Get priority if specified
                    priority = original_request.get("priority", "normal")
                    timeout = original_request.get("timeout_seconds")
                    
                    # Submit the request to the async system
                    result = generation_adapter.submit_async_request(
                        request_data=original_request,
                        priority=priority,
                        timeout_seconds=timeout
                    )
                    return result
                else:
                    # Use the legacy async system
                    result = background_route_service(gen_requester, restful_request)
            else:
                # Process synchronously
                result = gen_requester.route_service(restful_request)
        else:
            logger.error(f"Error processing request: {original_request}")
            raise HTTPException(
                status_code=500,
                detail={"error": "service mismatch", "input": original_request},
            )
            
        # cleanup resources before returning request
        run_cleanup()
        
        if result is None:
            raise HTTPException(
                status_code=500,
                detail={"error": "service not found", "input": original_request},
            )
            
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
        raise HTTPException(
            status_code=500,
            detail={"error": str(simple_error), "input": original_request},
        )


@app.get("/service", summary="Get service definitions")
async def get_service_defs():
    """
    Return service definitions for all available services.
    """
    logger.info("Retrieving service definitions")
    all_services = []
    
    # get generation service list
    gen_services: list = get_generation_services()
    if gen_services:
        if ASYNC_ALLOW:
            for i in range(len(gen_services)):
                gen_services[i]["async_allow"] = ASYNC_ALLOW
                # Add enhanced async flag for new services
                gen_services[i]["enhanced_async_support"] = True
        all_services.extend(gen_services)
        logger.debug(f"generation models registered: {len(gen_services)}")
        
    # get property service list
    prop_services = get_property_services()
    if ASYNC_ALLOW:
        for i in range(len(prop_services)):
            prop_services[i]["async_allow"] = ASYNC_ALLOW
            # Add enhanced async flag for new services
            prop_services[i]["enhanced_async_support"] = True
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
        logger.warning(f"could not print types: {str(e)}")
        
    return JSONResponse(all_services)


@app.get("/admin/details", summary="Get server details")
def server_details():
    """
    Return server configuration details.
    """
    logger.info("Retrieving server details")
    config = get_config_instance().model_dump()
    
    # Add async configuration
    config["async"] = {
        "enabled": ASYNC_ALLOW,
        "config": async_config.dict(),
    }
    
    return JSONResponse(config)


# Add new endpoints for the enhanced async API

@app.get("/async/status/{request_id}", summary="Get async request status")
async def get_async_status(request_id: str = Path(..., description="The request ID")):
    """
    Get the status of an asynchronous request.
    """
    # Try to get the status from the property adapter first
    status = property_adapter.get_request_status(request_id)
    if status and "error" not in status:
        return status
    
    # If not found, try the generation adapter
    status = generation_adapter.get_request_status(request_id)
    if status and "error" not in status:
        return status
    
    # If not found in either adapter, return an error
    raise HTTPException(
        status_code=404,
        detail={"error": "Request not found", "request_id": request_id},
    )


@app.delete("/async/cancel/{request_id}", summary="Cancel async request")
async def cancel_async_request(request_id: str = Path(..., description="The request ID")):
    """
    Cancel an asynchronous request.
    """
    # Try to cancel the request in the property adapter first
    result = property_adapter.cancel_request(request_id)
    if result and "error" not in result:
        return result
    
    # If not found, try the generation adapter
    result = generation_adapter.cancel_request(request_id)
    if result and "error" not in result:
        return result
    
    # If not found in either adapter, return an error
    raise HTTPException(
        status_code=404,
        detail={"error": "Request not found or could not be canceled", "request_id": request_id},
    )


@app.get("/async/stats", summary="Get async system statistics")
async def get_async_stats():
    """
    Get statistics about the asynchronous request processing system.
    """
    property_stats = property_adapter.get_queue_stats()
    generation_stats = generation_adapter.get_queue_stats()
    
    return {
        "property_service": property_stats,
        "generation_service": generation_stats,
        "config": async_config.dict(),
    }


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
    logger.debug(f"Server Config: {get_config_instance().model_dump()}")
    if get_config_instance().SERVE_MAX_WORKERS > 0:
        # overwite max workers with env var
        max_workers = get_config_instance().SERVE_MAX_WORKERS
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

    config_settings = GT4SDConfiguration().model_dump(include=['OPENAD_S3_HOST','OPENAD_S3_HOST_HUB'])
    logger.info(f"S3 Config: {config_settings}")
   
    logger.debug(f"Total workers: {max_workers}")
    # process is run on linux. spawn.
    multiprocessing.set_start_method("spawn")
    with ProcessPoolExecutor() as executor:
        executor.submit(run_main_service, host, port, log_level, max_workers)
        if is_running_in_kubernetes():
            logger.debug("Running in Kubernetes, starting health probe")
            executor.submit(run_health_service, host, port + 1, log_level, 1)
        signal.signal(signal.SIGINT, lambda s, f: signal_handler(s, f, executor))
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler(s, f, executor))
        signal.signal(signal.SIGWINCH, ignore_winch_signal)
        # Keep the main process running to handle signals and wait for child processes
        executor.shutdown(wait=True)
        
    # Shutdown the async adapters
    shutdown_adapters(wait=True)


if __name__ == "__main__":
    start_server()
