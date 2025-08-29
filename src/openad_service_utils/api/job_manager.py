""" " This module enables running of jobs by the wrapper
as parallel processes supporting asychrnous and synchronous user interaction"""

import uuid
import traceback
import gc
import ast
import os
from typing import List, Dict
import asyncio
from redis.asyncio import Redis
import uuid
from typing import List, Tuple, Dict
from redis import RedisError
from typing import Any, Callable, Dict, Tuple, Union, Optional
import pickle
import json, time
import multiprocessing as mp
import random
import logging
import pandas
from pathlib import Path
from multiprocessing import Pool
import aiofiles
from openad_service_utils.api.config import get_config_instance

# Create a logger
logger = logging.getLogger(__name__)

# Get the server configuration environment variables
settings = get_config_instance()

# QUEUES defines the number of sub processess allocated to a Pool of Worker Daemons to process requests
QUEUES = settings.REDIS_JOB_QUEUES

SUBMISSION_QUEUE = "submissions"  # redis submission queue for general jobs

ASYNC_SUBMISSION_QUEUE = "async_submissions"  # redis queue for asyncrhonous jobs

# ASYNC_PATH defines the path all async jobs results get saved to
ASYNC_PATH = settings.ASYNC_JOB_PATH

# ASYNC_CLEANUP_AGE defines the age in days that async results are cleaned up after
ASYNC_CLEANUP_AGE = settings.ASYNC_CLEANUP_AGE

# ASYNC_QUEUE_ALLOCATION defines the number of subprocesses allocated from the pool to process async requests
ASYNC_QUEUE_ALLOCATION = settings.ASYNC_QUEUE_ALLOCATION

# ASYNC_ALLOW turns async requests on and off
ASYNC_ALLOW = settings.ASYNC_ALLOW


class JobManager:
    """The Job manager class is designed to manage jobs running in OpenAD Daemons or workers
    it has 2 roles:
          1> as a API for commuicating with Workers and Submitting and retrieving jobs from Redis Quesues
          2> as the process for independant workers that run as asynchronous processes under the server"""

    def __init__(self, redis_client: Redis, Name: str, Async_enabled=False):
        """Initialize the JobManager object with a redis client and a name"""
        self.redis_client = redis_client
        self.name = Name
        self.async_enabled = Async_enabled

    async def get_all_jobs(self):
        """Retrieve all jobs' information from Redis."""

        job_info_list = []
        for key in await self.redis_client.keys("job:*"):
            job_id = key.decode().split(":")[1]  # Extract the job ID from the key
            job_info = await self._get_job_info_by_id(job_id)
            job_info_list.append(job_info)

        return job_info_list

    async def submit_job(self, instance: Any, methodname: str, args: Dict[str, Any] = {}, async_submission=False, file_keys: Optional[List[str]] = None): # Changed args type hint
        """Submit New Jobs to appropriate quueses
        ASYNC_SUBMISSION_QUEUE is the queue for asynchronous jobs
        SUBMISSION_QUEUE is for submitted jobs

        jobs are only pulled of the queues one a worker/Daemon is ready to process it.
        The standard SUBMISSION_QUEUE is cleared on restart

        All submitted jobs are set to expire and cleared from redis ater 4 days by default
        """
        job_id = str(uuid.uuid4())  # Create a unique job_id

        # Store the function information and arguments in the queue
        await self.redis_client.set(
            f"job:{job_id}",
            pickle.dumps(
                {
                    "instance": instance,
                    "methodname": methodname,
                    "args": args,
                    "result": None,
                    "error": False,
                    "status": "Submitted",
                    "job_id": job_id,
                    "async": async_submission,
                    "file_keys": file_keys, # Store file_keys in job_info
                }
            ),
        )

        await self.redis_client.expire(f"job:{job_id}", 345600)  # Expire all jobs in cache after 4 days
        logger.debug(f"Job {job_id} submitted to redis {self.name} with async submission: {async_submission}")
        if not async_submission:
            await self.redis_client.rpush(SUBMISSION_QUEUE, job_id)  # type: ignore
        else:
            await self.redis_client.rpush(ASYNC_SUBMISSION_QUEUE, job_id)  # type: ignore
            await self.___write_job_header_file__(args, job_id)

        return job_id

    async def ___write_job_header_file__(self, restful_request, job_id) -> str:
        """writes the job descriptor to file for asynchrounous jobs"""
        async with aiofiles.open(f"{ASYNC_PATH}/{job_id}.request", "w") as fd:
            await fd.write(json.dumps(restful_request))
        return f"{ASYNC_PATH}/{job_id}.request" # Return the path
        return f"{ASYNC_PATH}/{job_id}.request" # Return the path

    async def _get_job_info_by_id(self, job_id) -> Optional[Dict[str, Any]]: # Added return type hint
        """looks for a synchronous job if it s compled by its job id"""
        try:
            job_info_bytes = await self.redis_client.get(f"job:{job_id}")
            if job_info_bytes:
                job_info = pickle.loads(job_info_bytes)
                return job_info
            return None
        except Exception as e:
            logger.error(f"Error retrieving job info for {job_id}: {e}")
            return None

    async def get_result_by_id(self, job_id: str) -> Dict[str, Any]: # Changed return type to Dict[str, Any]
        try:
            job_info = await self._get_job_info_by_id(job_id)

            if job_info is None:
                return {"status": "failed", "error": f"Job {job_id} not found or expired."}

            if job_info["status"] == "completed":
                return job_info["result"]
            elif job_info["status"] == "error":
                return {"status": "error", "error": f"Job {job_id} encountered an error: {job_info.get('exception', 'Unknown error')}"}
            else:
                # Job is still running or not found, wait for a short period and try again
                while job_info["status"] not in ["error", "completed", "failed"]:
                    await asyncio.sleep(0.5)
                    job_info = await self._get_job_info_by_id(job_id)
                    if job_info is None: # Check again if job_info became None during waiting
                        return {"status": "failed", "error": f"Job {job_id} not found or expired during wait."}

                return job_info

        except (RedisError, asyncio.TimeoutError) as e:
            return {"status": "error", "error": f"Failed to retrieve job result for ID {job_id}: {str(e)}"}

    async def process_jobs(self):
        """process active jobs as part of the Daemon process by pulling them off Submission QUEUES

        Not async jobs are a lower priority and only will be enabled for pooled async enabled workers"""
        logger.debug(f"Starting Process Daemon {self.name} Async Enabled {self.async_enabled}")
        try:
            while True:
                job_id = None
                async_job = False
                task: bytes = await self.redis_client.lpop(SUBMISSION_QUEUE)  # type: ignore
                if task is not None:
                    job_id = task.decode()
                    # logger.debug(f" Job Allocated Process Daemon {self.name} Async Queue looking {job_id}")
                elif self.async_enabled:
                    await cleanup_old_files(localRepo=ASYNC_PATH, age=ASYNC_CLEANUP_AGE)
                    async_task: bytes = await self.redis_client.lpop(ASYNC_SUBMISSION_QUEUE)  # type: ignore
                    if async_task is not None:
                        job_id = async_task.decode()
                        async_job = True
                else:
                    await asyncio.sleep(0.1)
                    continue

                if job_id is not None:
                    job_info = await self._get_job_info_by_id(job_id)
                    if job_info is None:
                        logger.warning(f"Job {job_id} not found in Redis, skipping processing.")
                        await asyncio.sleep(0.1)
                        continue

                    logger.debug(f"Job {job_id} has been pulled off queue to be processed by Daemon {self.name}")
                    
                    instance = job_info["instance"]
                    methodname = job_info["methodname"]
                    args = job_info["args"]
                    file_keys = job_info.get("file_keys", []) # Retrieve file_keys
                    logger.debug(f"Job {job_id} file_keys: {file_keys}")

                    # Ensure args is a dictionary
                    if isinstance(args, bytes):
                        args = json.loads(args.decode())
                    elif isinstance(args, str) and not settings.ENABLE_CACHE_RESULTS:
                        logger.warning(f"args is not a dict. {type(args)=}")
                        args = json.loads(args)
                    elif not isinstance(args, dict):
                        logger.error(f"Job {job_id} args is not a dictionary or string, got {type(args)}. Attempting to convert.")
                        try:
                            args = json.loads(str(args))
                        except (json.JSONDecodeError, ValueError):
                            args = {} # Fallback to empty dict if conversion fails

                    job_info["status"] = "In Progress"
                    await self.redis_client.set(f"job:{job_id}", pickle.dumps(job_info))

                    if async_job:
                        async with aiofiles.open(f"{ASYNC_PATH}/{job_id}.running", "w") as fd:
                            await fd.write("")
                    
                    try:
                        logger.info(f"Running Job {job_id}")
                        instance = instance()
                        # Resolve file_keys to file_keys before passing to the predictor
                        resolved_file_paths = []
                        for key in file_keys:
                            path = await self.redis_client.get(f"file_map:{key}")
                            if path:
                                path = path.decode()
                                resolved_file_paths.append(path)
                                logger.debug(f"Resolved file key {key} to path {path}")
                            else:
                                logger.warning(f"File key {key} not found in Redis during job processing.")
                        
                        # if resolved_file_paths:
                        #     if "file_keys" not in args:
                        #         args["file_keys"] = []
                        #     args["file_keys"].extend(resolved_file_paths)

                        if async_job:
                            async with aiofiles.open(f"{ASYNC_PATH}/{job_id}.running", "w") as fd:
                                await fd.write("run")
                        result = await asyncio.to_thread(instance.route_service, args, resolved_file_paths)
                        logger.debug(f"Job {job_id} result: {result}")
                        job_info["result"] = result
                        job_info["status"] = "completed"
                        if async_job:
                            async with aiofiles.open(f"{ASYNC_PATH}/{job_id}.result", "w") as fd:
                                if isinstance(result, pandas.DataFrame):
                                    result = result.to_json()
                                await fd.write(json.dumps(result))
                        logger.info(f"Completed Job: {job_id}")

                    except Exception as e:
                        logger.error(f"Error processing job {job_id}: {str(e)}")
                        logger.error(traceback.format_exc())
                        if async_job:
                            result = {"error": str(e)}
                            async with aiofiles.open(f"{ASYNC_PATH}/{job_id}.result", "w") as fd:
                                await fd.write(json.dumps(result))
                        
                        job_info["result"] = {"error": str(e)}
                        job_info["error"] = True
                        job_info["status"] = "error"
                    finally:
                        # Cleanup temporary files and Redis entries
                        for key in file_keys:
                            temp_file_path = await self.redis_client.get(f"file_map:{key}")
                            if temp_file_path and os.path.exists(temp_file_path):
                                logger.debug(f"Removing temporary file for upload: {temp_file_path}")
                                os.remove(temp_file_path)
                            await self.redis_client.delete(f"file_map:{key}")
                        
                    await self.redis_client.set(f"job:{job_id}", pickle.dumps(job_info))
                    run_cleanup()
        except Exception as e:
            logger.error("Exception     " + str(e), exc_info=True)


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


def slave_thread(extra_q, async_allow=False):
    """create a slave thread and starte it for Daemon Workers"""
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD)
    daemon = JobManager(redis_client, f"{extra_q}", async_allow)
    asyncio.run(daemon.process_jobs())


async def get_slaves() -> list:
    """Loops through the number of slaves to create"""
    extra_queues = QUEUES
    daemons = []
    slave_pool = Pool(processes=extra_queues)

    while extra_queues > 0:
        if extra_queues <= ASYNC_QUEUE_ALLOCATION and ASYNC_ALLOW:
            daemons.append(slave_pool.apply_async(slave_thread, [extra_queues, ASYNC_ALLOW]))
        else:
            daemons.append(slave_pool.apply_async(slave_thread, [extra_queues]))
        extra_queues = extra_queues - 1

    return daemons


async def get_job_manager() -> JobManager:
    """creates a new job manager"""
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD)
    job_manager = JobManager(redis_client, " Master Queue")

    return job_manager  # Return the global job_manager instance


async def delete_sync_submission_queue():
    """cleares out the Submission Queue"""
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD)
    await redis_client.delete(SUBMISSION_QUEUE)
    logger.warning("Deleted Submission Queue")


async def cleanup_old_files(localRepo=ASYNC_PATH, age=3):
    """Cleans up old archive files"""
    if not os.path.exists(localRepo):
        os.mkdir(localRepo)
    critical_time = time.time() - age * 24 * 3600

    for item in Path(localRepo).expanduser().rglob("*"):
        if item.is_file():
            if os.stat(item).st_mtime < critical_time:
                os.remove(item)

    for item in Path(localRepo).expanduser().rglob("*"):
        if item.is_dir():
            if len(os.listdir(item)) == 0:
                os.rmdir(item)


async def retrieve_async_job(url) -> dict:
    """retrieves Async Jobs from Disk"""
    await cleanup_old_files(localRepo=ASYNC_PATH, age=3)
    requested = os.path.exists(f"{ASYNC_PATH}/{url}.request")
    running = os.path.exists(f"{ASYNC_PATH}/{url}.running")
    finished = os.path.exists(f"{ASYNC_PATH}/{url}.result")
    if finished:
        try:
            async with aiofiles.open(f"{ASYNC_PATH}/{url}.result", "r") as fd:
                content = await fd.read()
                result = json.loads(content)
                logger.info("Successfully retrieved job: " + url)
                return result
        except Exception as e:
            logger.warning("User attempted to retrieve non existing job: " + url)
            return None
    elif running:
        return {"warning": {"reason": "job is still running"}}

    elif requested:
        return {"warning": {"reason": "job is still in the queue"}}
    else:
        logger.warning("User attempted to retrieve non existing job: " + url)
        return None
