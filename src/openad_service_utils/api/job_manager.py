""" " This module enables running of jobs by the wrapper
as parallel processes supporting asychrnous and synchronous user interaction"""

import uuid
import traceback
import gc
import os
from typing import List, Dict
import asyncio
from redis.asyncio import Redis
from typing import Any, Dict, Optional
import pickle
import json, time
import logging
import pandas
from pathlib import Path
from redis import RedisError
import aiofiles
import shutil
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.common.models import FileResponse

# Create a logger
logger = logging.getLogger(__name__)

# Get the server configuration environment variables
settings = get_config_instance()



class JobManager:
    """The Job manager class is designed to manage jobs running in OpenAD Daemons or workers
    it has 2 roles:
          1> as a API for commuicating with Workers and Submitting and retrieving jobs from Redis Quesues
          2> as the process for independant workers that run as asynchronous processes under the server"""

    def __init__(self, redis_client: Redis, name: str):
        """Initialize the JobManager object with a redis client and a name"""
        self.redis_client = redis_client
        self.name = name

    async def get_all_jobs(self):
        """Retrieve all jobs' information from Redis."""
        job_info_list = []
        keys = await self.redis_client.keys("job:*")
        for key in keys:
            job_id = key.split(":")[1]  # Extract the job ID from the key
            job_info = await self._get_job_info_by_id(job_id)
            if job_info:
                job_info_list.append(job_info)
        return job_info_list

    async def submit_job(self, instance: Any, methodname: str, args: Dict[str, Any] = {}, async_submission=False, file_keys: Optional[List[str]] = None):
        """
        Submit a new job to the appropriate priority queue.
        Synchronous jobs go to the high-priority queue, asynchronous jobs to the low-priority queue.
        """
        job_id = str(uuid.uuid4())

        job_info = {
            "instance": instance,
            "methodname": methodname,
            "args": args,
            "result": None,
            "error": False,
            "status": "Submitted",
            "job_id": job_id,
            "async": async_submission,
            "file_keys": file_keys,
            "retries": 0,
        }

        await self.redis_client.set(f"job:{job_id}", pickle.dumps(job_info))
        await self.redis_client.expire(f"job:{job_id}", 345600)  # Expire all jobs in cache after 4 days

        if async_submission:
            await self.redis_client.rpush(settings.REDIS_LOW_PRIORITY_QUEUE, job_id)
            await self.___write_job_header_file__(args, job_id)
        else:
            await self.redis_client.rpush(settings.REDIS_HIGH_PRIORITY_QUEUE, job_id)

        return job_id

    async def ___write_job_header_file__(self, restful_request, job_id) -> str:
        """writes the job descriptor to file for asynchrounous jobs"""
        async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.request", "w") as fd:
            await fd.write(json.dumps(restful_request))
        return f"{settings.ASYNC_JOB_PATH}/{job_id}.request"

    async def _get_job_info_by_id(self, job_id) -> Optional[Dict[str, Any]]:
        """looks for a synchronous job if it s compled by its job id"""
        try:
            job_info_bytes = await self.redis_client.get(f"job:{job_id}")
            if job_info_bytes:
                return pickle.loads(job_info_bytes)
            return None
        except Exception as e:
            logger.error(f"Error retrieving job info for {job_id}: {e}")
            return None

    async def get_result_by_id(self, job_id: str) -> Dict[str, Any]:
        try:
            while True:
                job_info = await self._get_job_info_by_id(job_id)
                if job_info is None:
                    return {"status": "failed", "error": f"Job {job_id} not found or expired."}

                if job_info["status"] in ["completed", "error", "failed"]:
                    return job_info
                
                await asyncio.sleep(0.5)

        except (RedisError, asyncio.TimeoutError) as e:
            return {"status": "error", "error": f"Failed to retrieve job result for ID {job_id}: {str(e)}"}

    async def process_jobs(self):
        """
        Process jobs from high and low priority queues.
        This method uses BLPOP to wait for jobs and prioritizes the high-priority queue.
        """
        logger.debug(f"Starting Process Daemon {self.name}")
        queues = [settings.REDIS_HIGH_PRIORITY_QUEUE, settings.REDIS_LOW_PRIORITY_QUEUE]
        
        while True:
            try:
                # BLPOP waits for a job and returns the queue name and job_id
                result = await self.redis_client.blpop(queues)
                if result is None:
                    continue

                _, job_id_bytes = result
                job_id = job_id_bytes.decode()

                job_info = await self._get_job_info_by_id(job_id)
                if job_info is None:
                    logger.warning(f"Job {job_id} not found in Redis, skipping processing.")
                    continue

                instance = job_info["instance"]
                args = job_info["args"]
                file_keys = job_info.get("file_keys", [])
                async_job = job_info.get("async", False)

                priority = "Low" if async_job else "High"
                logger.info(f"[{self.name}] Processing {priority} Priority Job {job_id} from queue")

                job_info["status"] = "In Progress"
                await self.redis_client.set(f"job:{job_id}", pickle.dumps(job_info))

                if async_job:
                    await cleanup_old_files(localRepo=settings.ASYNC_JOB_PATH, age=settings.ASYNC_CLEANUP_AGE)
                    async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.running", "w") as fd:
                        await fd.write("")
                
                try:
                    instance = instance()
                    resolved_file_paths = []
                    for key in file_keys:
                        path = await self.redis_client.get(f"file_map:{key}")
                        if path:
                            resolved_file_paths.append(path.decode())
                        else:
                            logger.warning(f"[{self.name}] File key {key} not found in Redis during job processing.")
                    
                    result = await asyncio.to_thread(instance.route_service, args, file_keys=resolved_file_paths)

                    if async_job and isinstance(result, FileResponse):
                        persistent_path = os.path.join(settings.ASYNC_JOB_PATH, f"{job_id}.result")
                        shutil.move(result.file_path, persistent_path)
                        shutil.rmtree(os.path.dirname(result.file_path), ignore_errors=True)
                        job_info["result"] = {
                            "file_path": persistent_path,
                            "filename": os.path.basename(result.file_path),
                        }
                    else:
                        job_info["result"] = result

                    job_info["status"] = "completed"

                    if async_job and not isinstance(result, FileResponse):
                        async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.result", "w") as fd:
                            if isinstance(result, pandas.DataFrame):
                                result = result.to_json()
                            await fd.write(json.dumps(result))
                    logger.info(f"[{self.name}] Completed Job: {job_id}")

                except Exception as e:
                    error_message = traceback.format_exc()
                    logger.error(f"[{self.name}] Error processing job {job_id}: {error_message}")
                    
                    job_info["retries"] = job_info.get("retries", 0) + 1
                    if job_info["retries"] <= settings.JOB_MAX_RETRIES:
                        logger.info(f"[{self.name}] Requeuing job {job_id} (attempt {job_info['retries']})")
                        job_info["status"] = "Requeued"
                        await self.redis_client.set(f"job:{job_id}", pickle.dumps(job_info))
                        await asyncio.sleep(settings.JOB_RETRY_DELAY)
                        queue = settings.REDIS_LOW_PRIORITY_QUEUE if async_job else settings.REDIS_HIGH_PRIORITY_QUEUE
                        await self.redis_client.rpush(queue, job_id)
                    else:
                        logger.error(f"Job {job_id} failed after {settings.JOB_MAX_RETRIES} retries.")
                        job_info["result"] = {"error": error_message}
                        job_info["error"] = True
                        job_info["status"] = "failed"
                        if async_job:
                            async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.result", "w") as fd:
                                await fd.write(json.dumps(job_info["result"]))
                
                if job_info["status"] not in ["Requeued"]:
                    await self.redis_client.set(f"job:{job_id}", pickle.dumps(job_info))
                
                run_cleanup()

            except Exception as e:
                logger.error(f"[{self.name}] An error occurred in the main worker loop: {e}", exc_info=True)
                await asyncio.sleep(1) # Avoid rapid-fire errors

def run_cleanup():
    if settings.AUTO_CLEAR_GPU_MEM:
        try:
            import torch
            logger.debug(f"cleaning gpu memory for process ID: {os.getpid()}")
            torch.cuda.empty_cache()
        except ImportError:
            pass
    if settings.AUTO_GARBAGE_COLLECT:
        logger.debug(f"manual garbage collection on process ID: {os.getpid()}")
        gc.collect()

def slave_thread(worker_id):
    """create a slave thread and starte it for Daemon Workers"""
    logger.info(f"Started job worker {worker_id} with process with PID: {os.getpid()}")
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD)
    daemon = JobManager(redis_client, f"worker-{worker_id}")
    asyncio.run(daemon.process_jobs())

async def get_job_manager() -> JobManager:
    """creates a new job manager"""
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD)
    return JobManager(redis_client, "Master Queue")

async def clear_job_queues():
    """cleares out the Submission Queue"""
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD)
    await redis_client.delete(settings.REDIS_HIGH_PRIORITY_QUEUE)
    await redis_client.delete(settings.REDIS_LOW_PRIORITY_QUEUE)
    logger.debug("Cleared Job Queues")

async def cleanup_old_files(localRepo=settings.ASYNC_JOB_PATH, age=3):
    """Cleans up old archive files"""
    if not os.path.exists(localRepo):
        os.mkdir(localRepo)
    critical_time = time.time() - age * 24 * 3600

    for item in Path(localRepo).expanduser().rglob("*"):
        if item.is_file():
            try:
                if os.stat(item).st_mtime < critical_time:
                    os.remove(item)
            except FileNotFoundError:
                continue # File might have been deleted by another process

    for item in Path(localRepo).expanduser().rglob("*"):
        if item.is_dir():
            try:
                if len(os.listdir(item)) == 0:
                    os.rmdir(item)
            except FileNotFoundError:
                continue # Directory might have been deleted by another process

async def retrieve_async_job(url) -> Optional[dict]:
    """retrieves Async Jobs from Disk"""
    await cleanup_old_files(localRepo=settings.ASYNC_JOB_PATH, age=3)
    requested = os.path.exists(f"{settings.ASYNC_JOB_PATH}/{url}.request")
    running = os.path.exists(f"{settings.ASYNC_JOB_PATH}/{url}.running")
    finished = os.path.exists(f"{settings.ASYNC_JOB_PATH}/{url}.result")
    if finished:
        try:
            job_manager = await get_job_manager()
            job_info = await job_manager._get_job_info_by_id(url)
            if job_info and isinstance(job_info.get("result"), dict) and "file_path" in job_info["result"]:
                return {
                    "status": "completed",
                    "result_type": "file",
                    "download_url": f"/service/download/{url}/{job_info['result']['filename']}",
                }

            async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{url}.result", "r") as fd:
                content = await fd.read()
                if not content:
                    return {"status": "error", "reason": "Result file is empty, which may indicate a file-based job that failed to store its path correctly."}
                result = json.loads(content)
                logger.info("Successfully retrieved job: " + url)
                return result
        except Exception as e:
            logger.warning(f"Error retrieving job {url}: {e}")
            return None
    elif running:
        return {"warning": {"reason": "job is still running"}}
    elif requested:
        return {"warning": {"reason": "job is still in the queue"}}
    else:
        logger.warning("User attempted to retrieve non existing job: " + url)
        return None
