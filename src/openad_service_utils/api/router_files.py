# ----------------------------
# region --- Imports & Config

# UPLOAD_STORAGE_DIR = ~/.openad_models/collection_uploads

# NOTE: Fetch files/results endpoints loads all items without sorting or
# pagination, which is instead handled by the frontend table component.
# This is not scalable for large numbers of files. If this ever becomes
# unmanageable, the table component can be updated to defer to server-side
# pagination, sorting, and filtering, and this endpoint should be updated
# accordingly. Documentation for this lives in the frontend repo.

# Std
import os
import re
import time
import uuid
import json
import random
import shutil
import asyncio
import logging
from typing import List
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import asynccontextmanager


# 3rd Party
import redis.asyncio as redis
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi import APIRouter, Depends, HTTPException, Request, FastAPI


# Internal
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.utils.logging_config import setup_logging
from openad_service_utils.common.properties.property_factory import PropertyFactory

# Set up logging configuration
setup_logging()

# Get configuration and logger
settings = get_config_instance()
logger = logging.getLogger(__name__)


# endregion
# ----------------------------
# region --- Lifespan & Dependencies


@asynccontextmanager
async def files_router_lifespan(app: FastAPI):
    """
    Lifespan manager for the files router.
    Starts and stops the file sync background task.
    """
    task = None
    if "get_mesh_property" in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
        task = asyncio.create_task(sync_files_periodically(app.state.redis))

    yield

    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.log("Background file sync task was cancelled.")


async def get_redis_client(request: Request) -> redis.Redis:
    """Dependency to get Redis client from app state."""
    return request.app.state.redis


def files_enabled():
    """Dependency to check if file collection endpoints are enabled."""
    return True  # TEMPORARY -- DELETE THIS
    if "get_mesh_property" not in PropertyFactory.AVAILABLE_PROPERTY_PREDICTOR_TYPES():
        raise HTTPException(
            status_code=404,
            detail="File collection endpoints are not available for this service configuration.",
        )
    else:
        logger.info("File collection endpoints are enabled")


# CREATE ROUTER
files_router = APIRouter(
    prefix="/service/ui/files",
    dependencies=[Depends(files_enabled)],
    # tags=["ALL FILE ROUTES"],
)

# endregion
# ----------------------------
# region --- DUMMY: Data


model_versions = ["v1", "v2", "v3"]
checkpoints = ["cp-001", "cp-002", "cp-003", "cp-004"]
dummy_file_results = []
dummy_job_names = [
    "informal_stingray",
    "noble_otter",
    "thoughtless_crocodile",
    "aggregate_wombat",
    "chilly_gecko",
    "inappropriate_gerbil",
    "working_caribou",
    "oral_guineafowl",
    "urban_tarantula",
    "heavy_canidae",
    "identical_impala",
    "juicy_cuckoo",
    "middle_wallaby",
    "preferred_catfish",
    "chemical_otter",
    "mass_lynx",
    "principal_parrotfish",
    "mute_ladybug",
    "parental_hare",
    "kind_jellyfish",
    "mere_dog",
    "watery_badger",
    "advanced_primate",
    "ethnic_emu",
    "primary_anaconda",
    "deep_platypus",
    "previous_rhinoceros",
    "wittering_cattle",
    "vocal_gazelle",
    "redundant_bug",
    "prospective_smelt",
    "evil_carp",
    "cruel_alligator",
    "preferred_scorpion",
    "democratic_salmon",
    "mathematical_wolverine",
    "fashionable_giraffe",
    "lucky_koala",
    "young_mollusk",
    "classical_rhinoceros",
    "shared_sturgeon",
    "modern_smelt",
    "welcome_llama",
    "wee_gorilla",
    "revolutionary_donkey",
    "vocal_worm",
    "dead_ox",
    "mad_pinniped",
    "cognitive_silkworm",
    "puny_dolphin",
    "head_anaconda",
    "notable_termite",
]


# endregion
# ----------------------------
# region --- DUMMY: Fetch: Jobs for table


# Job Item model
class JobItem(BaseModel):
    index_: int
    id: int  # Hidden field
    icon: str
    jobName: str
    fileCount: int
    completedDate: datetime | None
    duration: int | None
    status: str
    download: bool

    overflow: List[dict] | None
    meta_: Meta = Meta()


# Generate dummy jobs
job_statuses = [
    "running",
    "completed",
    "failed",
]
dummy_jobs = []
# fmt: off
for i in range(1, 51):
    status=random.choice(job_statuses)
    rd_starttime_secago = random.randint(1, 300000)
    rd_duration = int(rd_starttime_secago) if status == "completed" else None
    rd_duration_pretty = str(timedelta(seconds=rd_starttime_secago)) if status == "completed" else '-'
    rd_upload_date = NOW - timedelta(seconds=rd_starttime_secago) if status == "completed" else None
    rd_upload_date_pretty = rd_upload_date.strftime("%b %d, %Y at %H:%M") if status == "completed" else '-'
    dummy_jobs.append(
        JobItem(
            index_=i,
            id=random.randint(0,10000000),
            icon="icn-yes-full" if status == "completed" else "icn-no-full" if status == "failed" else "icn-progress",
            jobName=dummy_job_names[i % len(dummy_job_names)],
            fileCount=random.randint(2, 8),
            completedDate=rd_upload_date,
            duration=rd_duration,
            status=status,
            download=True,
            overflow= [{
                "value": "delete-job",
                "label": "Delete job",
                "action": "(row) => { row.callback('delete-job', row) }",
            }],
            meta_=Meta(
                error="Something went wrong" if status == "failed" else None,
                # note="This is a note." if random.randint(1, 1) == 1 else None,
                data={"Started on": rd_upload_date_pretty, "Completed on": rd_upload_date_pretty, "Duration": rd_duration_pretty, "Created by": "billy@ibm.com"},

            ),
        )
    )
# fmt: on


@files_router.get("/jobs-page", tags=["Jobs (dummy)"])
async def get_jobs_page(
    status_filter: str = None,  # Filter by status
    page: int = 1,  # Page number
    page_size: int = 1,  # Page size
    sort: str = None,  # Sort key
    limit: str = None,  # Limit results to list of indices, eg. ?limit=1,7,12
    query: str = None,  # Filter results by query string
):
    # time.sleep(1)

    # Store the types per key
    # - - -
    # We cycle through the first 50 rows to determine the type
    # of each key while proritizing str > int/float/datetime > bool > NoneType.
    # This is required for sorting.
    sort_key_type_map = {}
    for item in dummy_jobs[:50]:
        for key, val in dict(item).items():
            if key in sort_key_type_map:
                prev_key_type = sort_key_type_map[key]
                new_key_type = type(val)
                if new_key_type == str:
                    sort_key_type_map[key] = new_key_type
                elif (
                    new_key_type == int
                    or new_key_type == float
                    or new_key_type == datetime
                ):
                    if prev_key_type == bool or prev_key_type == type(None):
                        sort_key_type_map[key] = new_key_type
            else:
                sort_key_type_map[key] = type(val)
    # print("- - -\n\n", sort_key_type_map, "\n\n")

    # Filter items by status
    if status_filter:
        items_by_status = [item for item in dummy_jobs if item.status == status_filter]
    else:
        items_by_status = dummy_jobs

    # Filter items by list of indices
    if limit:
        limit = [int(i) for i in limit.split(",")]
        items_limited = [
            item for [i, item] in enumerate(items_by_status) if i + 1 in limit
        ]
    else:
        items_limited = items_by_status

    # Filter items by query string
    if query:
        results = []
        for item in items_limited:
            for key in item.dict():
                value_str = str(item.dict().get(key, ""))
                if query.lower() in value_str.lower():
                    results.append(item)
                    break
        items_filtered = results
    else:
        items_filtered = items_limited

    # Sort items
    def _sort(item):
        fallback = (
            0
            if sort_key_type_map.get(sort) in [int, float]
            else (
                datetime.now()
                if sort_key_type_map.get(sort) in [datetime]
                else "" if sort_key_type_map.get(sort) == str else False
            )
        )
        value = dict(item).get(sort, fallback)
        value = fallback if value is None else value
        return value

    reverse = sort.startswith("-") if sort else False
    sort = sort[1:] if reverse else sort
    items_sorted = sorted(items_filtered, key=_sort, reverse=reverse)

    # Paginate items
    skip = (page - 1) * page_size
    items_page = items_sorted[skip : skip + page_size]

    # List of filtered indices
    result_indices = (
        [item.index_ for item in items_sorted]
        if len(items_sorted) < len(dummy_jobs)
        else []
    )

    # Assemble result
    result = JobItemsResponse(
        total=len(items_sorted),
        totalPages=(len(items_sorted) + page_size - 1) // page_size,
        resultIndices=result_indices,
        page=page,
        pageSize=page_size,
        items=items_page,
    )

    return result


# endregion
# ----------------------------
# region --- Fetch: Files for table


class FileObject(BaseModel):
    """Individual file model, as consumed by the frontend table component"""

    collection_name: str
    filename: str
    file_key: str
    file_extension: str
    size_bytes: int
    created_at: datetime


class FileListResponse(BaseModel):
    """Files list endpoint response model"""

    files: List[FileObject]
    all_collections: List[str]


@files_router.get(
    "",
    summary="Get all files",
    tags=["Collections / Files"],
)
@files_router.get(
    "/collection/{collection_name}",
    summary="Get files by collection",
    tags=["Collections / Files"],
)
async def get_files(
    collection_name: str | None = None,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Returns all files, or files from a given collection.

    Args:
        collection_name: Optional collection name. If None, returns files from all collections

    Returns:
        FileListResponse: List of files and all collection names
    """
    if collection_name:
        validate_collection_name(collection_name)
        validate_collection_exists(collection_name)

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


async def _assemble_file_info(file_key: str, file_path_str: str | None) -> dict:
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
# region --- Fetch: File results for table


# @dummy
result_statuses = [
    "uploading",
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "failed",
]


class ResultObject(BaseModel):
    """Individual result model, as consumed by the frontend table component"""

    filename: str
    job_name: str
    model_version: str
    checkpoint: str
    size_bytes: int
    created_at: datetime
    completed_at: datetime


class ResultListResponse(BaseModel):
    """File results endpoint response model"""

    results: List[ResultObject]


@files_router.get("/{collection_name}/{filename}", tags=["Job Results"])
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
        ResultListResponse
    """
    validate_collection_name(collection_name)
    validate_filename(filename)
    validate_collection_exists(collection_name)  # %%%
    validate_file_exists(collection_name, filename)

    try:
        # Scan for result keys
        result_keys = [
            key async for key in redis_client.scan_iter(f"file_map:{collection_name}/*")
        ]

        # Handle empty results
        if not result_keys:
            return ResultListResponse(results=[])

        # Assemble result objects for frontend consumption
        results = []
        for key in result_keys:
            result_path_str = await redis_client.get(key)
            file_info = await _assemble_result_info(filename, result_path_str)
            results.append(file_info)

        # @dummy - sort is handled by frontend, just for demo purposes here
        results = sorted(results, key=lambda x: x.created_at, reverse=True)

        # Success response
        return ResultListResponse(results=results)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = "Error retrieving file results"
        raise HTTPException(status_code=500, detail=f"{error_msg}: {str(e)}") from e


async def _assemble_result_info(filename: str, result_path_str: str | None) -> dict:
    """
    Assemble result info for frontend consumption.

    Args:
        filename: The name of the file
        result_path_str: The file path string from Redis
    """

    # Placeholder values:
    job_name = random.choice(dummy_job_names)
    model_version = "v1"
    checkpoint = "cp-001"
    completed_at = datetime.now() - timedelta(days=random.randint(1, 3))

    result_size = 0
    created_at = None

    if result_path_str:
        result_path = Path(result_path_str)
        if await run_in_threadpool(result_path.exists):
            stat_info = await run_in_threadpool(result_path.stat)
            result_size = stat_info.st_size
            created_at = stat_info.st_ctime * 1000  # Convert to milliseconds

    return ResultObject(
        filename=filename,
        job_name=job_name,
        model_version=model_version,
        checkpoint=checkpoint,
        size_bytes=result_size,
        created_at=created_at,
        completed_at=completed_at,
    )


# endregion
# ----------------------------
# region --- Create Jobset


@files_router.post(
    "create-jobset",
    summary="Create a new job set with a name and multiple files",
    tags=["Jobs / Create"],
)
async def create_jobset(jobset_name: str, files: List[str]):
    """
    Create a new job set with the given name and associated files.

    A job set is a group of jobs (each corresponding to a file)
    that are associated together under a common name.

    Note that to the user, the term "job set" is not exposed,
    for them this is simply a

    This calls the /service POST endpoint to create jobs for each file

    Args:
        jobset_name: Name of the job set to create
        files: List of file names to associate with the job set

    Returns:
        JSONResponse: Confirmation message with job set details
    """
    validate_jobset_name(jobset_name)


# endregion
# ----------------------------
# region --- Chunked Upload


@files_router.post(
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

    try:
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())

        # Create final collection directory if not exists
        # This is needed so we can open the collection page
        # while the files are being uploaded
        final_dir = Path(settings.UPLOAD_STORAGE_DIR) / filename
        final_dir.mkdir(parents=True, exist_ok=True)

        # Create temp directory for chunks
        temp_dir = Path(settings.UPLOAD_STORAGE_DIR) / "temp" / upload_id
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
        expiry_time = time.time() + (24 * 60 * 60)

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
        temp_dir = Path(settings.UPLOAD_STORAGE_DIR) / "temp" / upload_id
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500, detail=f"Error starting upload: {str(e)}"
        ) from e


@files_router.put(
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
    print("upload_chunk!")
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

        chunk_data = await request.body()
        expected_chunk_size = end_byte - start_byte + 1

        if len(chunk_data) != expected_chunk_size:
            raise HTTPException(
                status_code=400, detail="Chunk size doesn't match Content-Range"
            )

        # Store chunk to temp file
        chunk_filename = f"chunk_{start_byte}_{end_byte}"
        chunk_path = Path(metadata["temp_dir"]) / chunk_filename

        await run_in_threadpool(lambda: chunk_path.write_bytes(chunk_data))

        # Update received chunks tracking
        chunks_str = await redis_client.get(f"upload:{upload_id}:chunks")
        chunks_received = json.loads(chunks_str) if chunks_str else {}
        chunks_received[f"{start_byte}-{end_byte}"] = {
            "received_at": time.time(),
            "size": len(chunk_data),
            "chunk_file": chunk_filename,
        }

        await redis_client.set(
            f"upload:{upload_id}:chunks", json.dumps(chunks_received)
        )

        # Check if upload is complete
        total_received = sum(chunk["size"] for chunk in chunks_received.values())
        is_complete = total_received == metadata["total_size"]

        print(f'--- {metadata["total_size"]}/{total_received}')

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


@files_router.get(
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


@files_router.delete(
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
    completion_info: dict = None,
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

        # Assemble file
        # Note: this will overwrite existing file if present
        # Logic to prevent this lives under start_chunked_upload() -> replace/rename
        def write_assembled_file():
            with file_path.open("wb") as final_file:
                for start_byte, end_byte, chunk_info in sorted_chunks:
                    chunk_path = Path(metadata["temp_dir"]) / chunk_info["chunk_file"]
                    final_file.write(chunk_path.read_bytes())

        await run_in_threadpool(write_assembled_file)

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
        }
        await redis_client.set(
            f"upload:{upload_id}:completion", json.dumps(completion_info)
        )

        # Schedule cleanup (keep for 1 hour after completion)
        cleanup_time = time.time() + (60 * 60)
        await redis_client.set(f"upload:{upload_id}:ttl", str(cleanup_time))

        logger.info(
            "Successfully assembled file %s from chunked upload %s", filename, upload_id
        )

    except Exception as e:
        # Mark as failed
        error_info = {"status": "failed", "error": str(e), "failed_at": time.time()}
        await redis_client.set(f"upload:{upload_id}:completion", json.dumps(error_info))
        logger.error("Failed to assemble file from upload %s: %s", upload_id, str(e))


async def cleanup_upload_session(redis_client: redis.Redis, upload_id: str):
    """Clean up an upload session completely."""
    # Remove Redis keys
    keys_to_delete = [
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
    temp_dir = Path(settings.UPLOAD_STORAGE_DIR) / "temp" / upload_id
    if temp_dir.exists():
        await run_in_threadpool(shutil.rmtree, temp_dir, ignore_errors=True)


# endregion
# ----------------------------
# region --- Download


@files_router.get(
    "/download/{collection_name}/{filename}",
    summary="Download single file from collection",
    tags=["Collections / Download"],
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
# region --- Delete


@files_router.delete(
    "/{collection_name}",
    summary="Delete collection and all its files",
    tags=["Collections / Delete"],
)
async def delete_collection(
    collection_name: str, redis_client: redis.Redis = Depends(get_redis_client)
):
    """Deletes an entire collection and all of its files."""
    validate_collection_name(collection_name)
    try:
        collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
        if not collection_dir.is_dir():
            raise HTTPException(status_code=404, detail="Collection not found.")

        # Remove all files in the collection from Redis
        file_keys = [
            key async for key in redis_client.scan_iter(f"file_map:{collection_name}/*")
        ]

        if file_keys:
            await redis_client.delete(*file_keys)

        # Remove the collection directory from the filesystem
        shutil.rmtree(str(collection_dir))

        return JSONResponse(
            {"message": f"Collection '{collection_name}' deleted successfully."}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting collection: {str(e)}"
        ) from e


@files_router.delete(
    "/{collection_name}/{filename}",
    summary="Delete file",
    tags=["Collections / Delete"],
)
async def delete_file_from_collection(
    collection_name: str,
    filename: str,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Deletes a file from a specific collection."""
    validate_collection_name(collection_name)
    validate_filename(filename)
    try:
        file_key = str(Path(collection_name) / filename)
        file_path_str = await redis_client.get(f"file_map:{file_key}")

        if not file_path_str:
            raise HTTPException(status_code=404, detail="File not found.")

        file_path = Path(file_path_str)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found.")

        file_path.unlink()
        await redis_client.delete(f"file_map:{file_key}")

        return JSONResponse({"message": "File deleted successfully."})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting file: {str(e)}"
        ) from e


# endregion
# ----------------------------
# region --- Utility: Validators


def validate_jobset_name(jobset_name: str):
    """Validates the collection name for prohibited characters."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", jobset_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid job name, only alphanumeric characters, underscores and hyphens allowed.",
        )
    # TODO: this should also check for existing jobset names to ensure uniqueness


def validate_collection_name(collection_name: str):
    """Validates the collection name for prohibited characters."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", collection_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid collection name, only alphanumeric characters, underscores and hyphens allowed.",
        )


async def validate_collection_exists(collection_name: str):
    """Validates that the collection exists on the filesystem."""
    collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
    if not await run_in_threadpool(collection_dir.is_dir):
        raise HTTPException(status_code=404, detail="Collection not found.")


def validate_filename(filename: str):
    """Validates the filename for problematic characters."""
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


async def sync_files_to_redis(redis_client: redis.Redis):
    """Scans the upload directory and syncs the file index with Redis."""
    # logger.debug("Starting file sync to Redis...")

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
                            logger.warning(
                                "Skipping invalid filename during sync: %s", filename
                            )
            except HTTPException:
                logger.warning(
                    "Skipping invalid collection name during sync: %s", collection_name
                )

    # Add new files to Redis
    new_files = disk_files - redis_file_keys
    for file_key in new_files:
        full_path = os.path.join(settings.UPLOAD_STORAGE_DIR, file_key)
        await redis_client.set(f"file_map:{file_key}", full_path)
        logger.debug("Added new file to Redis: %s", file_key)

    # Remove deleted files from Redis
    deleted_files = redis_file_keys - disk_files
    if deleted_files:
        await redis_client.delete(*[f"file_map:{key}" for key in deleted_files])
        logger.debug("Removed deleted files from Redis: %s", deleted_files)


async def sync_files_periodically(redis_client: redis.Redis):
    """Runs the file sync process at a regular interval."""
    logger.info("Background file sync every 60 seconds has started...")
    while True:
        await sync_files_to_redis(redis_client)
        # Sync every 60 seconds
        await asyncio.sleep(settings.UPLOAD_STORAGE_SYNC_INTERVAL)


# endregion
# ----------------------------
