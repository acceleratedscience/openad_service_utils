# Optional endpoints for the file collections UI
# ----------------------------
# - Managing file collections
# - Chunked file upload
# - File download

# NOTE: Fetch endpoints load all items without sorting or pagination,
# which is instead handled by the frontend table component. This is
# not scalable for large numbers of files. If this ever becomes unmanageable,
# the table component can be updated to defer to server-side pagination,
# sorting, and filtering, and this endpoint should be updated accordingly.
# Documentation for this lives in the frontend repo.


# ----------------------------
# region --- Imports & Config

# Std
import asyncio
import hashlib
import json
import logging
import random
import re
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List

# 3rd Party
import redis.asyncio as redis
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
    File,
)
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from redis.exceptions import RedisError, LockError
from starlette.concurrency import run_in_threadpool

# Internal
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.api.dependencies import get_job_manager, get_redis_client
from openad_service_utils.api.job_manager import JobManager
from openad_service_utils.api.models import JobStatus
from openad_service_utils.utils.logging_config import setup_logging

# Set up logging configuration
setup_logging()

# Get configuration and logger
settings = get_config_instance()
logger = logging.getLogger(__name__)

# endregion
# ----------------------------
# region --- Pydantic models

# --- Files endpoint ---


class FileObject(BaseModel):
    """Individual file model, as consumed by the frontend table component."""

    collection_name: str
    filename: str
    file_key: str
    file_extension: str
    size_bytes: int
    created_at: datetime | float | None


class FileListResponse(BaseModel):
    """Return for files endpoint."""

    files: List[FileObject]
    all_collections: List[str]


# --- Jobs & File Results endpoints ---


class JobDetails(BaseModel):
    """
    Individual job model, as consumed by the frontend table component.

    Shared between /all-jobs and file results endpoints.
    """

    job_id: str
    filename: str
    collection_name: str
    model_version: str
    checkpoint: str
    size_bytes: int
    submission_time: datetime
    completion_time: datetime | None = None
    inference_time: float | None = None
    status: JobStatus


class JobsResponse(BaseModel):
    """Return for the /all-jobs endpoint."""

    jobs: List[JobDetails]


# endregion
# ----------------------------
# region --- Lifespan & Router Creation


@asynccontextmanager
async def files_router_lifespan(app: FastAPI):
    """
    Lifespan manager for the files router.
    Starts and stops the file sync background task.
    """
    task = asyncio.create_task(sync_files_periodically(app.state.redis))
    task = asyncio.create_task(cleanup_expired_uploads(app.state.redis))

    yield

    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Background file sync task was cancelled.")


# CREATE ROUTER
collections_router = APIRouter(
    prefix="/service/collections",
    # tags=["ALL FILE ROUTES"],
)


# endregion
# ----------------------------
# region --- Files: Fetch


@collections_router.get(
    "/{collection_name}/files",
    summary="Get files by collection",
    tags=["Collections / Files"],
)
@collections_router.get(
    "/files",
    summary="Get all files",
    tags=["Collections / Files"],
)
async def get_files(
    collection_name: str | None = None,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Returns all files, or files from a given collection.

    Note: download by collection name not currently used, filtering is handled by the frontend.

    Args:
        collection_name: Optional collection name. If None, returns files from all collections

    Returns:
        FileListResponse: List of files and all collection names
    """

    # @dummy test error
    # raise HTTPException(status_code=418, detail="This is a test.")

    if collection_name:
        validate_collection_name(collection_name)
        await validate_collection_exists(collection_name)

    # Fetch list of all collections, used to populate
    # dropdown which should be in sync at all times
    collection_names = await _get_all_collections(redis_client)

    try:
        # Scan for file keys
        scan_pattern = (
            f"file_map:{collection_name}/*" if collection_name else "file_map:*"
        )
        file_keys = [key async for key in redis_client.scan_iter(scan_pattern)]

        # No results
        if not file_keys:
            return FileListResponse(files=[], all_collections=collection_names)

        # Assemble file objects for frontend consumption
        files = []
        for key in file_keys:
            file_key = key.split(":")[1]
            file_path_str = await redis_client.get(key)
            file_info = await _assemble_file_info(file_key, file_path_str)
            files.append(file_info)

        # Success repsonse
        return FileListResponse(files=files, all_collections=collection_names)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = (
            "Error retrieving files from collection"
            if collection_name
            else "Error retrieving all files"
        )
        raise HTTPException(status_code=500, detail=f"{error_msg}: {str(e)}") from e


async def _assemble_file_info(file_key: str, file_path_str: str | None) -> FileObject:
    """
    Assemble file info for frontend consumption.

    Args:
        file_key: The Redis key for the file (format: collection_name/filename)
        file_path_str: The file path string from Redis
    """
    file_key_path = Path(file_key)
    collection_name = file_key_path.parts[0]
    filename = file_key_path.name

    file_size = 0
    created_at = None
    file_extension = ""

    if file_path_str:
        file_path = Path(file_path_str)
        file_extension = file_path.suffix.lower()

        if await run_in_threadpool(file_path.exists):
            stat_info = await run_in_threadpool(file_path.stat)
            file_size = stat_info.st_size
            created_at = stat_info.st_ctime * 1000  # Convert to milliseconds

    return FileObject(
        file_key=file_key,
        filename=filename,
        collection_name=collection_name,
        size_bytes=file_size,
        created_at=created_at,
        file_extension=file_extension,
    )


async def _get_all_collections(redis_client: redis.Redis) -> list[str]:
    """Returns a list of all available collections."""
    try:
        file_keys = [key async for key in redis_client.scan_iter("file_map:*")]
        all_collections = sorted(
            list(set([key.split(":")[1].split("/")[0] for key in file_keys]))
        )
        return all_collections
    except Exception as e:
        logger.error("Error fetching all collection names: %s", str(e))
        return []


# endregion
# ----------------------------
# region --- Files: Download


@collections_router.get(
    "/{collection_name}/{filename}/download",
    summary="Download single file from collection",
    tags=["Collections / Files"],
)
async def download_file_from_collection(
    collection_name: str,
    filename: str,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Downloads a file from a specific collection."""
    validate_collection_name(collection_name)
    validate_filename(filename)
    try:
        file_key = str(Path(collection_name) / filename)
        file_path_str = await redis_client.get(f"file_map:{file_key}")

        if not file_path_str:
            raise HTTPException(status_code=404, detail="File not found.")

        file_path = Path(file_path_str)
        if not await run_in_threadpool(file_path.exists):
            raise HTTPException(status_code=404, detail="File not found.")

        # Security check: ensure the file is within the upload storage directory
        storage_path = Path(settings.UPLOAD_STORAGE_DIR).resolve()
        if not file_path.resolve().is_relative_to(storage_path):
            raise HTTPException(
                status_code=403, detail="Access to this file is forbidden."
            )

        return FileResponse(
            path=str(file_path),
            media_type="application/octet-stream",
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading file: {str(e)}"
        ) from e


# endregion
# ----------------------------
# region --- Files: Delete


@collections_router.delete(
    "/{collection_name}",
    summary="Delete collection and all its files",
    tags=["Collections / Files"],
)
async def delete_collection(
    collection_name: str, redis_client: redis.Redis = Depends(get_redis_client)
):
    """Deletes an entire collection and all of its files."""
    validate_collection_name(collection_name)
    collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
    if not await run_in_threadpool(collection_dir.is_dir):
        raise HTTPException(status_code=404, detail="Collection not found.")
    try:
        # Remove all files in the collection from Redis
        file_keys = [
            key async for key in redis_client.scan_iter(f"file_map:{collection_name}/*")
        ]
        if file_keys:
            await redis_client.delete(*file_keys)
    except RedisError as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting collection from Redis: {str(e)}"
        ) from e
    try:
        # Remove the collection directory from the filesystem
        await run_in_threadpool(shutil.rmtree, str(collection_dir))
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting collection directory from filesystem: {str(e)}",
        ) from e
    return JSONResponse(
        {"message": f"Collection '{collection_name}' deleted successfully."}
    )


@collections_router.delete(
    "/{collection_name}/{filename}",
    summary="Delete file",
    tags=["Collections / Files"],
)
async def delete_file_from_collection(
    collection_name: str,
    filename: str,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Deletes a file from a specific collection."""
    # @dummy test error
    # if random.random() < 0.5:
    #     raise HTTPException(status_code=418, detail="This is a test.")
    validate_collection_name(collection_name)
    validate_filename(filename)
    try:
        file_key = str(Path(collection_name) / filename)
        lock_key = f"lock:file:{file_key}"
        async with redis_client.lock(
            lock_key, timeout=60, blocking=True, blocking_timeout=5
        ):
            file_path_str = await redis_client.get(f"file_map:{file_key}")
            if not file_path_str:
                raise HTTPException(status_code=404, detail="File not found in Redis.")
            file_path = Path(file_path_str)
            try:
                await run_in_threadpool(file_path.unlink)
            except FileNotFoundError:
                logger.warning(
                    "File %s not found on disk but was present in Redis. Deleting Redis entry.",
                    file_path,
                )
            await redis_client.delete(f"file_map:{file_key}")

        return JSONResponse({"message": "File deleted successfully."})
    except LockError:
        raise HTTPException(
            status_code=429,
            detail="Could not acquire lock for file operation. Please try again.",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting file: {str(e)}"
        ) from e


# endregion
# ----------------------------
# region --- Jobs: Fetch all


@collections_router.get(
    "/jobs",
    response_model=JobsResponse,
    tags=["Collections / Job Results"],
    summary="Get all job results",
)
async def get_all_jobs(
    redis_client: redis.Redis = Depends(get_redis_client),
) -> JobsResponse:
    """
    Returns a list of job dictionaries.
    """
    try:
        # @dummy test error
        # raise HTTPException(status_code=418, detail="This is a test.")

        job_keys = [key async for key in redis_client.scan_iter("job:*")]

        all_jobs = []
        for job_key in job_keys:
            job_info_str = await redis_client.get(job_key)
            if not job_info_str:
                continue
            job_info = json.loads(job_info_str)
            # results.append(job_info)

            file_keys = job_info.get("file_keys", [])
            collection_name = (
                file_keys[0].split("/")[0] if file_keys else "Missing collection name"
            )
            filename = file_keys[0].split("/")[1] if file_keys else "Missing filename"
            job = await _assemble_job_details(collection_name, filename, job_info)
            if job:
                all_jobs.append(job)

        return JobsResponse(jobs=all_jobs)
    except Exception as e:
        logger.error("Error retrieving job IDs: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Error retrieving job IDs: {str(e)}"
        ) from e


# endregion
# ----------------------------
# region --- Jobs: Fetch by file


@collections_router.get(
    "/{collection_name}/{filename}/jobs",
    tags=["Collections / Job Results"],
    summary="Get job results for a specific file",
)
async def get_file_results_page(
    collection_name: str,
    filename: str,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Returns all job results associated with a specific file.

    Args:
        collection_name: collection in which the file resides
        filename: name of the file

    Returns:
        JobsResponse
    """
    validate_collection_name(collection_name)
    validate_filename(filename)
    await validate_collection_exists(collection_name)
    await validate_file_exists(collection_name, filename)

    try:
        file_key = f"{collection_name}/{filename}"
        job_keys = [key async for key in redis_client.scan_iter("job:*")]

        # Filter jobs associated with the file key
        results = []
        for job_key in job_keys:
            job_info_str = await redis_client.get(job_key)
            if not job_info_str:
                continue

            job_info = json.loads(job_info_str)

            job_file_keys = job_info.get("file_keys")
            if not isinstance(job_file_keys, list) or file_key not in job_file_keys:
                continue

            # This job is associated with the file. Now create a Job object.
            job = await _assemble_job_details(collection_name, filename, job_info)
            if job:
                results.append(job)

        # Success response
        return JobsResponse(jobs=results)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = "Error retrieving file results"
        logger.error("%s: %s", error_msg, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"{error_msg}: {str(e)}") from e


async def _assemble_job_details(
    collection_name: str, filename: str, job_info: dict
) -> JobDetails | None:
    """
    Assemble result info for frontend consumption.

    Args:
        collection_name: The name of the collection
        filename: The name of the file
        job_info: The job info dictionary from Redis
    """

    job_id = job_info.get("job_id", "Missing job ID")

    size_bytes = 0
    if (
        job_info.get("result")
        and isinstance(job_info["result"], dict)
        and job_info["result"].get("file_path")
    ):
        result_path = Path(job_info["result"]["file_path"])
        if await run_in_threadpool(result_path.exists):
            stat_info = await run_in_threadpool(result_path.stat)
            size_bytes = stat_info.st_size

    model_version = "unknown"
    if (
        job_info.get("args")
        and isinstance(job_info["args"], dict)
        and job_info["args"].get("parameters", {}).get("algorithm_version")
    ):
        # TODO: Version to be implemented, not currently available in job args
        model_version = job_info["args"].get("parameters", {}).get("algorithm_version")

    submission_time = (
        datetime.fromtimestamp(job_info["submission_time"])
        if job_info.get("submission_time")
        else None
    )
    completion_time = (
        datetime.fromtimestamp(job_info["completion_time"])
        if job_info.get("completion_time")
        else None
    )

    if not submission_time:
        logger.warning(
            "Job %s has no submission time, skipping.", job_info.get("job_id")
        )
        return None

    return JobDetails(
        job_id=job_id,
        filename=filename,
        collection_name=collection_name,
        checkpoint="cp-001",  # TODO: Replace with actual checkpoint
        model_version=model_version,  # TODO: Model version not yet implemented, see above
        size_bytes=size_bytes,
        submission_time=submission_time,
        completion_time=completion_time,
        inference_time=job_info.get("inference_time"),
        status=job_info["status"],
    )


@collections_router.get(
    "/{job_id}/download",
    tags=["Collections / Job Results"],
    summary="Download job result file",
)
async def download_job_result(
    job_id: str, job_manager: JobManager = Depends(get_job_manager)
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

    if not isinstance(result, dict) or "file_path" not in result:
        raise HTTPException(
            status_code=404, detail="Result file not found for this job."
        )

    file_path = Path(result["file_path"])
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail="Result file not found for this job."
        )

    filename = result.get("filename", file_path.name)

    # Security check: ensure the file is within the async path
    if not file_path.is_relative_to(settings.ASYNC_JOB_PATH):
        raise HTTPException(status_code=403, detail="Access to this file is forbidden.")

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=filename,
    )


# endregion
# ----------------------------
# region --- Upload


# Single file direct upload
# Not used by the UI (it uses chunked upload below) but
# useful for benchmarking the server's upload speed.
@collections_router.post("/{collection_name}")
async def upload_file_to_collection(
    collection_name: str,
    file: UploadFile = File(...),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Uploads a file to a specific collection."""
    validate_collection_name(collection_name)
    try:
        filename = file.filename if file.filename else "uploaded_file"
        validate_filename(filename)

        collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
        collection_dir.mkdir(parents=True, exist_ok=True)
        file_path = collection_dir / filename

        await run_in_threadpool(shutil.copyfileobj, file.file, open(file_path, "wb"))

        file_key = f"{collection_name}/{filename}"
        await redis_client.set(f"file_map:{file_key}", file_path.as_posix())

        return JSONResponse(
            {"file_key": file_key, "message": "File uploaded successfully."}
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error uploading file: {str(e)}"
        ) from e


# Chunked file upload process:
# ----------------------------
# 1. Start Upload (POST /start):
#    - Validates inputs and creates a unique `upload_id`.
#    - Creates a temporary directory for chunks.
#    - Sets Redis keys:
#      - `upload:{id}:metadata`: Stores file info (filename, size, etc.).
#      - `upload:{id}:chunks`: Tracks received chunks.
#      - `upload:{id}:ttl`: Expiration timestamp for the session.
#
# 2. Upload Chunk (PUT /{upload_id}):
#    - Receives a binary chunk and validates Content-Range.
#    - Writes chunk to temp file.
#    - Updates `upload:{id}:chunks` with chunk info.
#    - If all chunks received:
#      - Triggers background assembly.
#      - Returns status "completing".
#
# 3. Background Assembly (`_assemble_file_from_chunks`):
#    - Concatenates chunks in order.
#    - Calculates SHA256 checksum.
#    - Moves final file to collection directory.
#    - Sets `upload:{id}:completion` with status "completed" and file info.
#    - Updates `upload:{id}:ttl` for short-term retention of completion status.
#
# 4. Get Status (GET /status):
#    - Returns progress based on `upload:{id}:chunks`.
#    - Checks `upload:{id}:completion` for final status (completed/failed).
#    - Used by frontend to poll for completion after last chunk.
#
# 5. Cleanup:
#    - `cleanup_expired_uploads` background task runs periodically.
#    - Removes Redis keys and temp directories for expired sessions (based on `:ttl`).


@collections_router.post(
    "/{collection_name}/upload/start",
    summary="Start chunked upload",
    tags=["Collections / Upload"],
)
async def start_chunked_upload(
    collection_name: str,
    filename: str,
    total_size: int,
    chunk_size: int = 5 * 1024 * 1024,  # 5MB default
    redis_client: redis.Redis = Depends(get_redis_client),
    # Options for second try:
    replace: bool = False,  # If filename exists, replace it
    rename: bool = False,  # If filename exists, add -1, -2, etc.
):
    """Start a chunked upload session."""

    # # @dummy test error
    # if random.random() < 0.5:
    #     raise HTTPException(status_code=418, detail="This is a test.")

    # Validate inputs
    validate_collection_name(collection_name)
    validate_filename(filename)
    if total_size <= 0:
        raise HTTPException(status_code=400, detail="Total size must be greater than 0")
    if chunk_size <= 0 or chunk_size > 50 * 1024 * 1024:  # Max 50MB per chunk
        raise HTTPException(
            status_code=400, detail="Chunk size must be between 1 byte and 50MB"
        )

    # Ansure the collection directory exists
    collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
    await run_in_threadpool(collection_dir.mkdir, parents=True, exist_ok=True)

    # If filename exists, send back to client to choose action (replace/rename)
    if not replace and not rename:
        await validate_filename_collision(redis_client, collection_name, filename)

    # Generate unique upload ID
    upload_id = str(uuid.uuid4())
    try:

        # Create final collection directory if not exists
        # This is needed so we can open the collection page
        # while the files are being uploaded
        final_dir = Path(settings.UPLOAD_STORAGE_DIR)
        final_dir.mkdir(parents=True, exist_ok=True)

        # Create temp directory for chunks
        temp_dir = (
            Path(settings.UPLOAD_STORAGE_DIR)
            / settings.UPLOAD_STORAGE_CHUNK_TEMP_DIR
            / upload_id
        )
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Calculate expected number of chunks
        total_chunks = (total_size + chunk_size - 1) // chunk_size

        # Handle duplicate filenames
        if rename:
            collection_dir.mkdir(parents=True, exist_ok=True)

            file_path = collection_dir / filename
            counter = 1
            original_filename = filename
            while file_path.exists():
                name_part = Path(original_filename).stem
                ext_part = Path(original_filename).suffix
                filename = f"{name_part}_{counter}{ext_part}"
                file_path = collection_dir / filename
                counter += 1

        # Store upload metadata in Redis
        metadata = {
            "upload_id": upload_id,
            "collection_name": collection_name,
            "filename": filename,
            "total_size": total_size,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
            "created_at": time.time(),
            "temp_dir": str(temp_dir),
        }

        # Set TTL for 24 hours
        expiry_time = time.time() + settings.UPLOAD_STORAGE_EXPIRATION

        await redis_client.set(f"upload:{upload_id}:metadata", json.dumps(metadata))
        await redis_client.set(
            f"upload:{upload_id}:chunks", json.dumps({})
        )  # Track received chunks
        await redis_client.set(f"upload:{upload_id}:ttl", str(expiry_time))

        return JSONResponse(
            {
                "upload_id": upload_id,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "expires_at": expiry_time,
                "message": f"Upload session started for '{filename}'. Send chunks to PUT /{collection_name}/upload/{upload_id}",
            }
        )

    except Exception as e:
        # Clean up on error
        temp_dir = (
            Path(settings.UPLOAD_STORAGE_DIR)
            / settings.UPLOAD_STORAGE_CHUNK_TEMP_DIR
            / upload_id
        )
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500, detail=f"Error starting upload: {str(e)}"
        ) from e


@collections_router.put(
    "/{collection_name}/upload/{upload_id}",
    summary="Upload chunk",
    tags=["Collections / Upload"],
)
async def upload_chunk(
    collection_name: str,
    upload_id: str,
    request: Request,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Upload a chunk using Content-Range header."""

    # # @dummy test error
    # if random.random() < 0.5:
    #     raise HTTPException(status_code=418, detail="This is a test.")

    # print("upload_chunk!")
    validate_collection_name(collection_name)

    # Get metadata
    metadata_str = await redis_client.get(f"upload:{upload_id}:metadata")
    if not metadata_str:
        raise HTTPException(
            status_code=404, detail="Upload session not found or expired"
        )

    metadata = json.loads(metadata_str)
    # print(metadata)

    # Verify collection matches
    if metadata["collection_name"] != collection_name:
        raise HTTPException(status_code=400, detail="Collection name mismatch")

    # Parse Content-Range header (format: bytes start-end/total)
    content_range = request.headers.get("content-range")
    if not content_range:
        raise HTTPException(status_code=400, detail="Content-Range header required")

    try:
        # Parse range: "bytes 0-1048575/5242880"
        range_part = content_range.replace("bytes ", "")
        range_info, total_str = range_part.split("/")
        start_byte, end_byte = map(int, range_info.split("-"))
        total_size = int(total_str)
        # print({range_part, range_info, start_byte, total_size})

        # Validate range
        if start_byte < 0 or end_byte < start_byte:
            raise HTTPException(status_code=400, detail="Invalid byte range")

        if total_size != metadata["total_size"]:
            raise HTTPException(status_code=400, detail="Total size mismatch")

        expected_chunk_size = end_byte - start_byte + 1

        # Stream body to a temporary file to avoid loading entire chunk into memory,
        # then atomically rename it to the final chunk path.
        chunk_filename = f"chunk_{start_byte}_{end_byte}"
        chunk_path = Path(metadata["temp_dir"]) / chunk_filename
        temp_path = chunk_path.with_suffix(f".tmp.{uuid.uuid4()}")
        bytes_written = 0
        try:
            with temp_path.open("wb") as f:
                async for chunk in request.stream():
                    await run_in_threadpool(f.write, chunk)
                    bytes_written += len(chunk)

            if bytes_written != expected_chunk_size:
                raise HTTPException(
                    status_code=400, detail="Chunk size doesn't match Content-Range"
                )

            await run_in_threadpool(temp_path.rename, chunk_path)

        except Exception:
            if await run_in_threadpool(temp_path.exists):
                await run_in_threadpool(temp_path.unlink)
            raise

        # Update received chunks tracking
        chunks_str = await redis_client.get(f"upload:{upload_id}:chunks")
        chunks_received = json.loads(chunks_str) if chunks_str else {}
        chunks_received[f"{start_byte}-{end_byte}"] = {
            "received_at": time.time(),
            "size": bytes_written,
            "chunk_file": chunk_filename,
        }

        await redis_client.set(
            f"upload:{upload_id}:chunks", json.dumps(chunks_received)
        )

        # Check if upload is complete
        total_received = sum(chunk["size"] for chunk in chunks_received.values())
        is_complete = total_received == metadata["total_size"]

        # print(f'--- {metadata["total_size"]}/{total_received}')

        # Build consistent response using shared function
        response = await _build_upload_status_response(
            upload_id, metadata, chunks_received, redis_client
        )

        # Add chunk-specific fields
        response["chunk_range"] = f"{start_byte}-{end_byte}"

        if is_complete:
            # Assemble final file in background
            asyncio.create_task(
                _assemble_file_from_chunks(
                    upload_id, metadata, chunks_received, redis_client
                )
            )
            response["status"] = "completing"
            response["message"] = "Upload complete, assembling file..."
        else:
            response["message"] = "Chunk received successfully"

        return JSONResponse(response)

    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid Content-Range format: {str(e)}"
        ) from e
    except Exception as e:
        logger.error("Error uploading chunk: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Error uploading chunk: {str(e)}"
        ) from e


@collections_router.get(
    "/{collection_name}/upload/{upload_id}/status",
    summary="Get upload status",
    tags=["Collections / Upload"],
)
async def get_upload_status(
    collection_name: str,
    upload_id: str,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Get the status of a chunked upload."""
    validate_collection_name(collection_name)

    # Get metadata
    metadata_str = await redis_client.get(f"upload:{upload_id}:metadata")
    if not metadata_str:
        raise HTTPException(
            status_code=404, detail="Upload session not found or expired"
        )

    metadata = json.loads(metadata_str)

    # Verify collection matches
    if metadata["collection_name"] != collection_name:
        raise HTTPException(status_code=400, detail="Collection name mismatch")

    # Get chunks status
    chunks_str = await redis_client.get(f"upload:{upload_id}:chunks")
    chunks_received = json.loads(chunks_str) if chunks_str else {}

    # Check if completed/failed
    completion_str = await redis_client.get(f"upload:{upload_id}:completion")
    completion_info = json.loads(completion_str) if completion_str else None

    # Build consistent response using shared function
    response = await _build_upload_status_response(
        upload_id, metadata, chunks_received, redis_client, completion_info
    )

    return JSONResponse(response)


@collections_router.delete(
    "/{collection_name}/upload/{upload_id}",
    summary="Cancel upload",
    tags=["Collections / Upload"],
)
async def cancel_upload(collection_name: str, upload_id: str, request: Request):
    """Cancel and clean up a chunked upload session."""
    validate_collection_name(collection_name)

    # Verify upload exists and collection matches
    metadata_str = await request.app.state.redis.get(f"upload:{upload_id}:metadata")
    if not metadata_str:
        raise HTTPException(status_code=404, detail="Upload session not found")

    metadata = json.loads(metadata_str)
    if metadata["collection_name"] != collection_name:
        raise HTTPException(status_code=400, detail="Collection name mismatch")

    # Clean up
    await cleanup_upload_session(request.app.state.redis, upload_id)

    return JSONResponse(
        {"upload_id": upload_id, "message": "Upload session cancelled and cleaned up"}
    )


async def _build_upload_status_response(
    upload_id: str,
    metadata: dict,
    chunks_received: dict,
    redis_client: redis.Redis,
    completion_info: dict | None = None,
) -> dict:
    """Build a consistent upload status response for both chunk uploads and status checks."""

    # Calculate progress
    total_received = sum(chunk["size"] for chunk in chunks_received.values())
    progress_percent = (
        (total_received / metadata["total_size"]) * 100
        if metadata["total_size"] > 0
        else 0
    )

    # Get TTL
    ttl_str = await redis_client.get(f"upload:{upload_id}:ttl")
    expires_at = float(ttl_str) if ttl_str else None

    # Base response structure
    response = {
        "upload_id": upload_id,
        "filename": metadata["filename"],
        "collection_name": metadata["collection_name"],
        "bytes_received": total_received,
        "bytes_total": metadata["total_size"],
        "progress_percent": round(progress_percent, 2),
        "chunks_received": len(chunks_received),
        "chunks_total": metadata["total_chunks"],
        "expires_at": expires_at,
        "created_at": metadata["created_at"],
    }

    # Add status-specific fields
    if completion_info:
        # Upload is completed or failed
        response.update(
            {
                "status": completion_info["status"],
                "completed_at": completion_info.get("completed_at"),
                "failed_at": completion_info.get("failed_at"),
                "error": completion_info.get("error"),
                "file_path": completion_info.get("file_path"),
                "file_key": completion_info.get("file_key"),
                "final_filename": completion_info.get("final_filename"),
                "file_size": completion_info.get("file_size"),
                "checksum": completion_info.get("checksum"),
            }
        )
    else:
        # Still uploading
        response["status"] = "uploading"

    return response


async def _assemble_file_from_chunks(
    upload_id: str, metadata: dict, chunks_received: dict, redis_client: redis.Redis
):
    """Assemble the final file from chunks in the background."""
    try:

        # # @dummy test error
        # if random.random() < 0.5:
        #     raise HTTPException(status_code=418, detail="This is a test.")

        collection_name = metadata["collection_name"]
        filename = metadata["filename"]

        # Create collection directory & final file path
        collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
        collection_dir.mkdir(parents=True, exist_ok=True)
        file_path = collection_dir / filename

        # Sort chunks by start byte position
        sorted_chunks = []
        for range_str, chunk_info in chunks_received.items():
            start_byte, end_byte = map(int, range_str.split("-"))
            sorted_chunks.append((start_byte, end_byte, chunk_info))

        sorted_chunks.sort(key=lambda x: x[0])

        # Assemble file & return sha256 hash as checksum
        # Note: this will overwrite existing file if present
        # Logic to prevent this lives under start_chunked_upload() -> replace/rename
        def write_assembled_file():
            sha256_hash = hashlib.sha256()
            with file_path.open("wb") as final_file:
                for start_byte, end_byte, chunk_info in sorted_chunks:
                    chunk_path = Path(metadata["temp_dir"]) / chunk_info["chunk_file"]
                    final_file.write(chunk_path.read_bytes())
                    sha256_hash.update(chunk_path.read_bytes())
            return sha256_hash.hexdigest()

        checksum = await run_in_threadpool(write_assembled_file)

        # @dummy checksum fail
        # checksum = "dummy_checksum_fail"

        # Update Redis file mapping
        file_key = str(Path(collection_name) / filename)
        await redis_client.set(f"file_map:{file_key}", str(file_path))

        # Mark upload as completed in Redis
        completion_info = {
            "status": "completed",
            "file_path": str(file_path),
            "file_key": file_key,
            "final_filename": filename,
            "completed_at": time.time(),
            "file_size": file_path.stat().st_size,
            "checksum": checksum,
        }
        await redis_client.set(
            f"upload:{upload_id}:completion", json.dumps(completion_info)
        )

        # Schedule cleanup after 10 minutes
        # - - -
        # We can't immediately run cleanup_upload_session() because the completion
        # signal is detected from the get_upload_status endpoint which is called
        # every second by the frontend, after the last chunk was uploaded, until
        # the file is assembled and the upload id is marked as completed.
        cleanup_time = time.time() + settings.UPLOAD_STORAGE_EXPIRATION_COMPLETE
        await redis_client.set(f"upload:{upload_id}:ttl", str(cleanup_time))

        logger.info(
            "Successfully assembled file %s from chunked upload %s", filename, upload_id
        )

    # Mark as failed
    except Exception as e:
        error_info = {"status": "failed", "error": str(e), "failed_at": time.time()}
        await redis_client.set(f"upload:{upload_id}:completion", json.dumps(error_info))
        logger.error("Failed to assemble file from upload %s: %s", upload_id, str(e))


async def cleanup_upload_session(
    redis_client: redis.Redis, upload_id: str, bg_task: bool = False
):
    """Clean up an upload session completely."""
    # Remove Redis keys
    keys_to_delete = [
        f"upload:{upload_id}:completion",
        f"upload:{upload_id}:metadata",
        f"upload:{upload_id}:chunks",
        f"upload:{upload_id}:ttl",
    ]
    existing_keys = []
    for key in keys_to_delete:
        if await redis_client.exists(key):
            existing_keys.append(key)

    if existing_keys:
        await redis_client.delete(*existing_keys)

    # Remove temp directory
    temp_dir = (
        Path(settings.UPLOAD_STORAGE_DIR)
        / settings.UPLOAD_STORAGE_CHUNK_TEMP_DIR
        / upload_id
    )
    if temp_dir.exists():
        _prefix = "\x1b[33mBG:Cleanup\x1b[0m " if bg_task else ""
        logger.debug(f"{_prefix}\x1b[31mRemoving temp dir: \x1b[0m%s", temp_dir)
        await run_in_threadpool(shutil.rmtree, temp_dir, ignore_errors=True)


# endregion
# ----------------------------
# region --- Data for UI


@collections_router.get(
    "/model-versions",
    summary="Get available model versions for dropdown",
    tags=["Collections / UI Data"],
)
async def get_model_versions():
    # TODO: Replace with actual model versions
    model_versions = ["v1"]
    return JSONResponse(content={"model_versions": model_versions})


@collections_router.get(
    "/job-statuses",
    summary="Get job status options for dropdown",
    tags=["Collections / UI Data"],
)
async def get_job_statuses():
    job_statuses = [member.value for member in JobStatus]
    return JSONResponse(content={"job_statuses": job_statuses})


# endregion
# ----------------------------
# region --- Utility: Validators


def validate_collection_name(collection_name: str):
    """Validates the collection name for prohibited characters."""
    if not re.match(r"^[a-zA-Z0-9_][a-zA-Z0-9_-]*$", collection_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid collection name. Must start with alphanumeric or underscore, and can contain hyphens.",
        )


async def validate_collection_exists(collection_name: str):
    """Validates that the collection exists on the filesystem."""
    collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
    if not await run_in_threadpool(collection_dir.is_dir):
        raise HTTPException(status_code=404, detail="Collection not found.")


def validate_filename(filename: str):
    """Validates the filename for problematic characters."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename. Directory traversal characters are not allowed.",
        )

    sanitized_filename = re.sub(r'[<>:"/\\|?*]', "-", filename)
    if filename != sanitized_filename:
        raise HTTPException(status_code=422, detail="Invalid filename.")


async def validate_file_exists(collection_name: str, filename: str):
    """Validates that the file exists on the filesystem."""
    file_path = Path(settings.UPLOAD_STORAGE_DIR) / collection_name / filename
    if not await run_in_threadpool(file_path.exists):
        raise HTTPException(status_code=404, detail="File not found.")


async def validate_filename_collision(
    redis_client: redis.Redis, collection_name: str, filename: str
):
    """Validates the filename uniqueness against existing filenames in the collection."""
    existing_filenames = [
        key[len(f"file_map:{collection_name}/") :]
        async for key in redis_client.scan_iter(f"file_map:{collection_name}/*")
    ]
    if filename in existing_filenames:
        raise HTTPException(
            status_code=409,
            detail=f"File '{filename}' already exists in collection '{collection_name}'.",
        )


# endregion
# ----------------------------
# region --- Background tasks


async def sync_files_periodically(redis_client: redis.Redis):
    """Background task: Syncs file system with Redis a regular interval."""
    logger.debug(
        "\x1b[33mBG:Sync START\x1b[0m -- Sync files every 60 seconds...\x1b[0m"
    )
    while True:
        await sync_files_to_redis(redis_client)
        # Sync every 60 seconds
        await asyncio.sleep(settings.UPLOAD_STORAGE_INTERVAL_SYNC)


async def sync_files_to_redis(redis_client: redis.Redis):
    """Scans the upload directory and syncs the file index with Redis."""
    # logger.debug("\x1b[33mBG:Sync\x1b[0m Syncing file system with Redis...")

    # Get all file keys from Redis
    redis_keys = [key async for key in redis_client.scan_iter("file_map:*")]
    redis_file_keys = {key.split(":")[1] for key in redis_keys}

    # Get all files from the filesystem, assuming subdirectories are collections
    disk_files = set()
    root_dir = Path(settings.UPLOAD_STORAGE_DIR)
    for collection in root_dir.iterdir():
        if collection.is_dir():
            try:
                validate_collection_name(collection.name)
                if collection.name in [
                    settings.UPLOAD_STORAGE_CHUNK_TEMP_DIR
                ]:  # Skip _temp folder
                    continue
                for file in collection.iterdir():
                    if file.is_file():
                        try:
                            validate_filename(file.name)
                            if file.name in [".DS_Store"]:  # Skip system files
                                continue
                            file_key = collection.name + "/" + file.name
                            disk_files.add(file_key)
                        except HTTPException:
                            logger.warning(
                                "\x1b[33mBG:Sync\x1b[0m Skipping invalid filename: %s",
                                file.name,
                            )
            except HTTPException as e:
                logger.warning(
                    "\x1b[33mBG:Sync\x1b[0m Skipping invalid collection name: %s (%s)",
                    collection.name,
                    e,
                )

    # Add new files to Redis
    new_files = disk_files - redis_file_keys
    for file_key in new_files:
        full_path = (root_dir / file_key).as_posix()
        await redis_client.set(f"file_map:{file_key}", full_path)
        logger.debug(
            "\x1b[33mBG:Sync\x1b[0m \x1b[32m[+] Added new file to Redis:\x1b[0m %s",
            file_key,
        )

    # Remove deleted files from Redis
    deleted_files = redis_file_keys - disk_files
    if deleted_files:
        await redis_client.delete(*[f"file_map:{key}" for key in deleted_files])
        for key in deleted_files:
            logger.debug(
                "\x1b[33mBG:Sync\x1b[0m \x1b[31m[-] Removed deleted file from Redis:\x1b[0m %s",
                key,
            )


async def cleanup_expired_uploads(redis_client: redis.Redis):
    """
    Background task: Cleans up expired upload sessions.

    Cleans up:
    - Chunk files from abandoned uploads after (24h)
    - Chunk files from completed upload metadata after (10m)
    - Redis keys associated with expired uploads
    """
    logger.debug(
        f"\x1b[33mBG:Cleanup START\x1b[0m -- Clean up expired uploads every {settings.UPLOAD_STORAGE_INTERVAL_CLEANUP} seconds..."
    )
    while True:
        try:
            # logger.debug("\x1b[33mBG:Cleanup\x1b[0m Cleaning up expired uploads...")
            current_time = time.time()
            upload_ttl_keys = [
                key async for key in redis_client.scan_iter("upload:*:ttl")
            ]

            for ttl_key in upload_ttl_keys:
                ttl_str = await redis_client.get(ttl_key)
                if not ttl_str:
                    continue

                expiry_time = float(ttl_str)
                if current_time > expiry_time:
                    # Extract upload_id from key
                    upload_id = ttl_key.split(":")[1]
                    logger.debug(
                        "\x1b[33mBG:Cleanup\x1b[0m \x1b[31mRemoving temp files for upload \x1b[0m%s",
                        upload_id,
                    )
                    await cleanup_upload_session(redis_client, upload_id, bg_task=True)

            # Sleep for the configured interval before next check
            await asyncio.sleep(settings.UPLOAD_STORAGE_INTERVAL_CLEANUP)

        except Exception as e:
            logger.error("Error during expired upload cleanup: %s", str(e))
            await asyncio.sleep(settings.UPLOAD_STORAGE_INTERVAL_CLEANUP)


# endregion
# ----------------------------
