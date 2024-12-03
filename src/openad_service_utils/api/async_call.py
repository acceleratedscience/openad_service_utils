# This code is designed to handle asynch requests
import pandas
import os
import time
from pathlib import Path
import multiprocessing as mp
import uuid
import json
import logging
from openad_service_utils.api.config import get_config_instance

POOL = None
ASYNC_PATH = "/tmp/openad_async_archive"

# Create a logger
logger = logging.getLogger(__name__)


def background_route_service(requestor, restful_request):
    """Runs Model calls in the backgound"""
    global POOL
    cleanup_old_files(localRepo=ASYNC_PATH, age=3)
    if POOL is None:
        POOL = mp.Pool(processes=get_config_instance().ASYNC_POOL_MAX)
    url = __create_job_url__(restful_request)
    POOL.apply_async(
        ___call_service___, [restful_request, requestor, url], callback=finished
    )
    ___write_job_header_file__(restful_request, url)
    logger.info(f"posted background process {url}")
    return {"id": url}


def finished(url):
    logger.info(f"Finsihed background process {url}")
    # Create a logger


def retrieve_job(url) -> dict:
    cleanup_old_files(localRepo=ASYNC_PATH, age=3)
    requested = os.path.exists(f"{ASYNC_PATH}/{url}.request")
    running = os.path.exists(f"{ASYNC_PATH}/{url}.running")
    finished = os.path.exists(f"{ASYNC_PATH}/{url}.result")
    if finished:
        try:
            with open(f"{ASYNC_PATH}/{url}.result", "r") as fd:
                result = json.load(fd)
                logger.info("Successfully retrieve job :" + url)
                return result
        except Exception as e:
            logger.warning("User attempted to retrieve not existing job: " + url)
            return None
    elif running:
        return {"warning": {"reason": "job is still running"}}

    elif requested:
        return {"warning": {"reason": "job is still in the queue"}}
    else:
        logger.warning("User attempted to retrieve not existing job: " + url)
        return None


def __create_job_url__(restful_request) -> str:
    """create job id"""
    url = uuid.uuid1()
    return url


def ___write_job_header_file__(restful_request, url) -> str:
    """writes the job descriptor to file"""
    with open(f"{ASYNC_PATH}/{url}.request", "w") as fd:
        fd.write(json.dumps(restful_request))
        fd.close()
    return url


def ___call_service___(restful_request: dict, requestor, url):
    """calls the inference task"""
    with open(f"{ASYNC_PATH}/{url}.running", "w") as fd:
        fd.write("")
        fd.close()
    try:
        result = requestor.route_service(restful_request)
        with open(f"{ASYNC_PATH}/{url}.running", "w") as fd:
            fd.write(str(result))
            fd.close()
        with open(f"{ASYNC_PATH}/{url}.running", "w") as fd:
            fd.write("run")
            fd.close()
    except Exception as e:
        result = {"error": str(e)}
        with open(f"{ASYNC_PATH}/{url}.running", "w") as fd:
            fd.write(str(result))
            fd.close()
    try:
        with open(f"{ASYNC_PATH}/{url}.result", "w") as fd:
            if isinstance(result, pandas.DataFrame):
                result = result.to_json()
            fd.write(json.dumps(result))
            fd.close()
    except Exception as e:
        result = {"error": str(e)}
        with open(f"{ASYNC_PATH}/{url}.result", "w") as fd:
            fd.write(json.dumps(result))
            fd.close()
    return url


def cleanup_old_files(localRepo=ASYNC_PATH, age=3):
    """Cleans up old archive files"""
    if not os.path.exists(ASYNC_PATH):
        os.mkdir(ASYNC_PATH)
    critical_time = time.time() - age * 24 * 3600

    for item in Path(localRepo).expanduser().rglob("*"):
        if item.is_file():
            if os.stat(item).st_mtime < critical_time:
                os.remove(item)

    for item in Path(localRepo).expanduser().rglob("*"):
        if item.is_dir():
            if len(os.listdir(item)) == 0:
                os.rmdir(item)
