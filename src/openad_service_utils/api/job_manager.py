""" " This module enables running of jobs by the wrapper
as parallel processes supporting asychrnous and synchronous user interaction"""

import asyncio
from async_timeout import timeout
import gc
import importlib
import json
import logging
import os
import shutil
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import pandas
from redis import RedisError
from redis.asyncio import Redis

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

    def _get_instance_from_path(self, class_path: str) -> Any:
        """Dynamically imports a class from a string path."""
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import instance from path: {class_path}")
            raise e

    async def get_all_jobs(self):
        """Retrieve all jobs' information from Redis."""
        job_info_list = []
        async for key in self.redis_client.scan_iter("job:*"):
            job_id = key.split(":")[1]
            job_info = await self._get_job_info_by_id(job_id)
            if job_info:
                job_info_list.append(job_info)
        return job_info_list

    async def submit_job(
        self,
        instance: Any,
        methodname: str,
        args: Dict[str, Any] = {},
        async_submission=False,
        file_keys: Optional[List[str]] = None,
        submission_time: Optional[float] = None,
    ):
        """
        Submit a new job to the appropriate priority queue.
        Synchronous jobs go to the high-priority queue, asynchronous jobs to the low-priority queue.
        """
        job_id = str(uuid.uuid4())

        job_info = {
            "instance_class_path": f"{instance.__module__}.{instance.__name__}",
            "methodname": methodname,
            "submission_time": submission_time,
            "completion_time": None,
            "inference_time": None,
            "args": args,
            "result": None,
            "error": False,
            "status": "Submitted",
            "job_id": job_id,
            "async": async_submission,
            "file_keys": file_keys,
            "retries": 0,
        }

        await self.redis_client.set(f"job:{job_id}", json.dumps(job_info), ex=settings.JOB_TTL)

        if async_submission:
            logger.info(f"Submitted async job: {job_id}")
            _ = await self.redis_client.rpush(settings.REDIS_LOW_PRIORITY_QUEUE, job_id)
            await self.___write_job_header_file__(args, job_id)
        else:
            logger.info(f"Submitted synchronous job: {job_id}")
            _ = await self.redis_client.rpush(settings.REDIS_HIGH_PRIORITY_QUEUE, job_id)

        return job_id

    async def ___write_job_header_file__(self, restful_request, job_id) -> str:
        """writes the job descriptor to file for asynchrounous jobs"""
        async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.request", "w") as fd:
            await fd.write(json.dumps(restful_request))
        return f"{settings.ASYNC_JOB_PATH}/{job_id}.request"

    async def _get_job_info_by_id(self, job_id) -> Optional[Dict[str, Any]]:
        """return job id data"""
        try:
            job_info_bytes = await self.redis_client.get(f"job:{job_id}")
            if job_info_bytes:
                return json.loads(job_info_bytes)
            return None
        except Exception as e:
            logger.error(f"Error retrieving job info for {job_id}: {e}")
            return None

    async def get_result_by_id(self, job_id: str) -> Dict[str, Any]:
        """Waits for a job to complete using Redis Pub/Sub and returns the result."""
        try:
            # First, check if the job is already completed to avoid unnecessary pub/sub
            job_info = await self._get_job_info_by_id(job_id)
            if job_info and job_info["status"] in ["completed", "error", "failed"]:
                return job_info

            if job_info is None:
                return {"status": "failed", "error": f"Job {job_id} not found or expired."}

            # If not completed, use Pub/Sub to wait for a notification
            pubsub = self.redis_client.pubsub()
            channel = f"job_completed:{job_id}"
            await pubsub.subscribe(channel)

            try:
                # Re-check status after subscribing to close the race condition window.
                job_info_after_sub = await self._get_job_info_by_id(job_id)
                if job_info_after_sub and job_info_after_sub["status"] in ["completed", "error", "failed"]:
                    logger.debug(f"Job {job_id} completed before waiting on Pub/Sub.")
                    return job_info_after_sub

                # Wait for a message on the channel with a timeout
                async with timeout(settings.JOB_COMPLETION_TIMEOUT):
                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            logger.debug(f"Received completion notification for job {job_id}")
                            break  # Exit loop once a message is received
            
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for completion notification for job {job_id}")
                # It's good practice to do one final check after a timeout
                final_job_info = await self._get_job_info_by_id(job_id)
                if final_job_info and final_job_info["status"] in ["completed", "error", "failed"]:
                    return final_job_info
                return {"status": "error", "error": f"Timeout waiting for job {job_id} to complete."}

            finally:
                # Ensure we always unsubscribe
                await pubsub.unsubscribe(channel)

            # Fetch the final job information
            final_job_info = await self._get_job_info_by_id(job_id)
            if final_job_info:
                return final_job_info
            else:
                # This case might happen if the job expires right after completion
                return {"status": "failed", "error": f"Could not retrieve final result for job {job_id}."}

        except (RedisError, asyncio.TimeoutError) as e:
            logger.error(f"Error while waiting for job result for ID {job_id}: {str(e)}")
            return {"status": "error", "error": f"Failed to retrieve job result for ID {job_id}: {str(e)}"}

    async def process_jobs(self):
        """
        Process jobs from high and low priority queues.
        This method uses BLPOP to wait for jobs and prioritizes the high-priority queue.
        """
        logger.debug(f"Starting Process Daemon {self.name}")
        queues = [settings.REDIS_HIGH_PRIORITY_QUEUE, settings.REDIS_LOW_PRIORITY_QUEUE]
        
        while True:
            job_id = None  # Initialize job_id for this loop iteration
            job_info = None # Initialize job_info to prevent unbound local error
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

                instance_class = self._get_instance_from_path(job_info["instance_class_path"])
                args = job_info["args"]
                file_keys = job_info.get("file_keys", [])
                async_job = job_info.get("async", False)

                priority = "Low" if async_job else "High"
                logger.info(f"[{self.name}] Processing {priority} Priority Job {job_id} from queue")

                job_info["status"] = "In Progress"
                await self.redis_client.set(f"job:{job_id}", json.dumps(job_info))

                if async_job:
                    await cleanup_old_files(localRepo=settings.ASYNC_JOB_PATH, age=settings.ASYNC_CLEANUP_AGE)
                    async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.running", "w") as fd:
                        await fd.write("")
                
                try:
                    start_time = time.time()
                    instance = instance_class()
                    resolved_file_paths = []
                    for key in file_keys:
                        path = await self.redis_client.get(f"file_map:{key}")
                        if path:
                            resolved_file_paths.append(path.decode())
                        else:
                            logger.warning(f"[{self.name}] File key {key} not found in Redis during job processing.")
                    
                    result = await asyncio.to_thread(instance.route_service, args, file_keys=resolved_file_paths)
                    end_time = time.time()
                    job_info["inference_time"] = round(end_time - start_time, 2)
                    job_info["completion_time"] = end_time

                    if result is None:
                        raise ValueError("Service returned an unexpected None result.")

                    # 1. Transform raw result for consistent JSON output
                    if isinstance(result, pandas.DataFrame):
                        result = result.to_dict(orient="records")
                    elif isinstance(result, (str, int, float, bool)):
                        result = {"result": result}
                    logger.warning(f"result: {result}")
                    # 2. Handle result based on its type (FileResponse or data)
                    if isinstance(result, FileResponse):
                        # Handle file-based results
                        file_path = result.file_path
                        filename = os.path.basename(file_path)
                        if async_job:
                            # For async jobs, move the file to a persistent location
                            persistent_path = os.path.join(settings.ASYNC_JOB_PATH, f"{job_id}.result")
                            shutil.move(file_path, persistent_path)
                            shutil.rmtree(os.path.dirname(file_path), ignore_errors=True)
                            job_info["result"] = {
                                "file_path": persistent_path,
                                "filename": filename,
                            }
                        else:
                            # For sync jobs, use the temporary path
                            job_info["result"] = {
                                "file_path": file_path,
                                "filename": filename,
                            }
                    else:
                        # Handle data-based results
                        job_info["result"] = result
                        if async_job:
                            # For async jobs, write data to a result file
                            async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.result", "w") as fd:
                                await fd.write(json.dumps(result))

                    # 3. Finalize job status
                    job_info["status"] = "completed"
                    logger.info(f"[{self.name}] Completed Job: {job_id}")

                except Exception as e:
                    error_message = traceback.format_exc()
                    logger.error(f"[{self.name}] Error processing job {job_id}: {error_message}")
                    
                    job_info["retries"] = job_info.get("retries", 0) + 1
                    if job_info["retries"] <= settings.JOB_MAX_RETRIES:
                        logger.info(f"[{self.name}] Requeuing job {job_id} (attempt {job_info['retries']})")
                        job_info["status"] = "Requeued"
                        await self.redis_client.set(f"job:{job_id}", json.dumps(job_info))
                        await asyncio.sleep(settings.JOB_RETRY_DELAY)
                        queue = settings.REDIS_LOW_PRIORITY_QUEUE if async_job else settings.REDIS_HIGH_PRIORITY_QUEUE
                        _ = await self.redis_client.rpush(queue, job_id)
                    else:
                        logger.error(f"Job {job_id} failed after {settings.JOB_MAX_RETRIES} retries.")
                        job_info["result"] = {"error": str(e)}
                        job_info["error"] = True
                        job_info["status"] = "failed"
                        if async_job:
                            async with aiofiles.open(f"{settings.ASYNC_JOB_PATH}/{job_id}.result", "w") as fd:
                                await fd.write(json.dumps(job_info["result"]))
                
                if job_info["status"] not in ["Requeued"]:
                    await self.redis_client.set(f"job:{job_id}", json.dumps(job_info))
                
            except Exception as e:
                logger.error(f"[{self.name}] An error occurred in the main worker loop: {e}", exc_info=True)
                if job_id:
                    try:
                        # Attempt to fetch job_info again, as it might not be available from the try block
                        job_info = await self._get_job_info_by_id(job_id)
                        if job_info:
                            job_info["status"] = "failed"
                            job_info["error"] = True
                            job_info["result"] = {"error": f"A critical error occurred in the worker: {str(e)}"}
                            await self.redis_client.set(f"job:{job_id}", json.dumps(job_info))
                        else:
                            # If job_info cannot be fetched, we can't do much more.
                            logger.error(f"[{self.name}] Could not retrieve job info for {job_id} to mark as failed.")
                    except Exception as inner_e:
                        logger.error(f"[{self.name}] Failed to update job {job_id} to failed status: {inner_e}", exc_info=True)
                await asyncio.sleep(1) # Avoid rapid-fire errors
            
            finally:
                # After processing, publish a notification for synchronous waiters
                if job_id and job_info and not job_info.get("async", False) and job_info["status"] not in ["Requeued"]:
                    channel = f"job_completed:{job_id}"
                    await self.redis_client.publish(channel, "completed")
                run_cleanup()


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
    logger.debug(f"Started job worker {worker_id} with process with PID: {os.getpid()}")
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB, password=settings.REDIS_PASSWORD)
    daemon = JobManager(redis_client, f"worker-{worker_id}")
    asyncio.run(daemon.process_jobs())


async def clear_job_queues(redis_client: Redis):
    """cleares out the Submission Queue"""
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


async def retrieve_async_job(url: str, redis_client: Redis) -> Optional[dict]:
    """retrieves Async Jobs from Disk"""
    await cleanup_old_files(localRepo=settings.ASYNC_JOB_PATH, age=3)
    requested = os.path.exists(f"{settings.ASYNC_JOB_PATH}/{url}.request")
    running = os.path.exists(f"{settings.ASYNC_JOB_PATH}/{url}.running")
    finished = os.path.exists(f"{settings.ASYNC_JOB_PATH}/{url}.result")
    if finished:
        try:
            job_manager = JobManager(redis_client, "async_retriever")
            job_info = await job_manager._get_job_info_by_id(url)
            if job_info and isinstance(job_info.get("result"), dict) and "file_path" in job_info["result"]:
                file_path = job_info["result"]["file_path"]
                size_bytes = 0
                if await asyncio.to_thread(os.path.exists, file_path):
                    size_bytes = await asyncio.to_thread(os.path.getsize, file_path)
                return {
                    "status": "completed",
                    "submission_time": job_info["submission_time"],
                    "completion_time": job_info["completion_time"],
                    "inference_time": job_info["inference_time"],
                    "result_type": "file",
                    "download_url": f"/service/download/{url}/{job_info['result']['filename']}",
                    "size_bytes": size_bytes,
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
