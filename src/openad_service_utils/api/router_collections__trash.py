# ----------------------------
# region --- Setup

# UPLOAD_STORAGE_DIR = ~/.openad_models/collection_uploads

# Std
import time
import uuid
import json
import shutil
import asyncio
import logging
import zipfile
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta


# 3rd Party
import redis.asyncio as redis
from starlette.concurrency import run_in_threadpool
from starlette.background import BackgroundTask
from fastapi import APIRouter, Depends, File
from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

# Utils
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.utils.validation import (
    validate_collection_name,
    validate_filename,
    validate_filename_collision,
)

# Get configuration and logger
settings = get_config_instance()
logger = logging.getLogger(__name__)


async def get_redis_client(request: Request) -> redis.Redis:
    """Dependency to get Redis client from app state."""
    return request.app.state.redis


collections_router = APIRouter(
    prefix="/service/collections",
    # dependencies=[Depends(get_redis_client)],
    tags=["collections"],
)

# endregion
# ----------------------------
# region --- System routes


@collections_router.get("/health", response_class=HTMLResponse)
async def collections_router_health():
    return "UP"


@collections_router.get("/names")
async def get_collections(redis_client: redis.Redis = Depends(get_redis_client)):
    """Returns a list of all available collections."""
    try:
        file_keys = [key async for key in redis_client.scan_iter("file_map:*")]
        collections = sorted(
            list(set([key.split(":")[1].split("/")[0] for key in file_keys]))
        )
        return JSONResponse({"collections": collections})
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving collections: {str(e)}"
        ) from e


@collections_router.post("/reindex")
async def reindex_redis_from_filesystem(
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Reindex the Redis database to match the current state of the filesystem.

    This function scans the upload storage directory and updates Redis to reflect
    the current state of the files on disk. Any missing or outdated entries in Redis
    will be corrected.

    Args:
        redis_client: The Redis client instance.
    """
    try:
        logger.info("Starting Redis reindexing from filesystem...")
        storage_path = Path(settings.UPLOAD_STORAGE_DIR)
        if not storage_path.is_dir():
            raise HTTPException(
                status_code=500, detail="Upload storage directory does not exist."
            )

        # Scan the filesystem for all files
        for collection_dir in storage_path.iterdir():
            if collection_dir.is_dir():
                collection_name = collection_dir.name
                for file_path in collection_dir.iterdir():
                    if file_path.is_file():
                        file_key = str(Path(collection_name) / file_path.name)
                        await redis_client.set(f"file_map:{file_key}", str(file_path))

        # Clean up Redis keys that no longer exist on disk
        redis_keys = [key async for key in redis_client.scan_iter("file_map:*")]
        for key in redis_keys:
            file_path_str = await redis_client.get(key)
            if file_path_str and not Path(file_path_str).exists():
                await redis_client.delete(key)

        logger.info("Redis database successfully reindexed to match filesystem.")
    except Exception as e:
        logger.error("Error reindexing Redis database: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Error reindexing Redis database: {str(e)}"
        ) from e


# endregion
# ----------------------------
# region --- DUMMY ROUTES: File Results

# Generate dummy jobs
algoVersions = ["v1", "v2", "v3"]
checkpoints = ["cp-001", "cp-002", "cp-003", "cp-004"]
dummy_file_results = []
job_names = [
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
# fmt: off
import random
# from datetime import datetime
file_statuses = [
    "uploading",
    "completed",
    "completed",
    "completed",
    "completed",
    "completed",
    "failed",
]
from pydantic import BaseModel
class Meta(BaseModel):
    error: Optional[str] = None
    note: Optional[str] = None
    data: Optional[dict] = None

class FileResultItem(BaseModel):
    index_: int
    id: int  # Hidden field
    icon: str
    jobName: str
    algoVersion: str
    checkpoint: str
    completed: datetime | None
    duration: int | None
    status: str
    download: bool

    overflow: List[dict] | None
    meta_: Meta = Meta()

# Items response models
from typing import Union, TypeVar

# Generic type for items
ItemType = TypeVar('ItemType')

class FileResultsResponse(BaseModel):
    total: int
    totalPages: int
    resultIndices: List[int]
    page: int
    pageSize: int
    items: List[FileResultItem]

class JobItemsResponse(BaseModel):
    total: int
    totalPages: int
    resultIndices: List[int]
    page: int
    pageSize: int
    items: List['JobItem']  # Forward reference since JobItem is defined later

NOW = datetime.now()
for i in range(1, 5):
    status=random.choice(file_statuses)
    rd_starttime_secago = random.randint(1, 300000)
    rd_duration = int(rd_starttime_secago) if status == "completed" else None
    rd_duration_pretty = str(timedelta(seconds=rd_starttime_secago)) if status == "completed" else '-'
    rd_upload_date = NOW - timedelta(seconds=rd_starttime_secago) if status == "completed" else None
    rd_upload_date_pretty = rd_upload_date.strftime("%b %d, %Y at %H:%M") if status == "completed" else '-'
    dummy_file_results.append(
        FileResultItem(
            index_=i,
            id=random.randint(0,10000000),
            icon="icn-yes-full" if status == "completed" else "icn-no-full" if status == "failed" else "icn-progress",
            jobName=job_names[i % len(job_names)],
            algoVersion=random.choice(algoVersions),
            checkpoint=random.choice(checkpoints),
            completed=rd_upload_date,
            duration=rd_duration,
            status=status,
            download=True,
            overflow= [{
                "value": "delete-file-result",
                "label": "Delete result",
                "action": "(row) => { row.callback('delete-file-result', row) }",
            }],
            meta_=Meta(
                error="Something went wrong" if status == "failed" else None,
                # note="This is a note." if random.randint(1, 1) == 1 else None,
                data={"Started on": rd_upload_date_pretty, "Completed on": rd_upload_date_pretty, "Duration": rd_duration_pretty, "Created by": "billy@ibm.com"},

            ),
        )
    )
# fmt: on


@collections_router.get("/file-results-page")
async def get_file_results_page(
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
    for item in dummy_file_results[:50]:
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

    # Filter items by list of indices
    if limit:
        limit = [int(i) for i in limit.split(",")]
        items_limited = [
            item for [i, item] in enumerate(dummy_file_results) if i + 1 in limit
        ]
    else:
        items_limited = dummy_file_results

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
        if len(items_sorted) < len(dummy_file_results)
        else []
    )

    # Assemble result
    result = FileResultsResponse(
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
# region --- DUMMY ROUTES: Jobs


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
            jobName=job_names[i % len(job_names)],
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


@collections_router.get("/jobs-page")
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
# region --- Basic Upload (unused)


# Single file upload not useful, keeping for reference
# @collections_router.post("/{collection_name}")
# async def upload_file_to_collection(collection_name: str, file: UploadFile = File(...)):
#     """Uploads a file to a specific collection."""
#     validate_collection_name(collection_name)
#     try:
#         filename = file.filename if file.filename else "uploaded_file"
#         validate_filename(filename)
#         collection_dir = os.path.join(settings.UPLOAD_STORAGE_DIR, collection_name)
#         os.makedirs(collection_dir, exist_ok=True)

#         file_path = os.path.join(collection_dir, filename)
#         # Offload blocking file write to a thread pool
#         await run_in_threadpool(shutil.copyfileobj, file.file, open(file_path, "wb"))

#         file_key = os.path.join(collection_name, filename)
#         await app.state.redis.set(f"file_map:{file_key}", file_path)

#         return JSONResponse({"file_key": file_key, "message": "File uploaded successfully."})
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@collections_router.post("/{collection_name}")
async def upload_files_to_collection_v1(
    collection_name: str,
    files: List[UploadFile] = File(...),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Uploads one or more files to a specific collection."""
    validate_collection_name(collection_name)

    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    uploaded_files = []
    errors = []

    try:
        collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
        collection_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            try:
                filename = (
                    file.filename
                    if file.filename
                    else f"uploaded_file_{len(uploaded_files) + 1}"
                )
                validate_filename(filename)

                file_path = collection_dir / filename

                # Handle duplicate filenames by appending a counter
                counter = 1
                original_filename = filename
                while file_path.exists():
                    original_path = Path(original_filename)
                    filename = f"{original_path.stem}_{counter}{original_path.suffix}"
                    file_path = collection_dir / filename
                    counter += 1

                # Offload blocking file write to a thread pool
                with open(file_path, "wb") as f:
                    await run_in_threadpool(shutil.copyfileobj, file.file, f)

                file_key = str(Path(collection_name) / filename)
                await redis_client.set(f"file_map:{file_key}", str(file_path))

                uploaded_files.append(
                    {
                        "file_key": file_key,
                        "filename": filename,
                        "original_filename": file.filename,
                        "size_bytes": file_path.stat().st_size,
                    }
                )

            except Exception as file_error:
                errors.append({"filename": file.filename, "error": str(file_error)})

        response_data = {
            "uploaded_files": uploaded_files,
            "total_uploaded": len(uploaded_files),
            "message": f"Successfully uploaded {len(uploaded_files)} file(s) to collection '{collection_name}'.",
        }

        if errors:
            response_data["errors"] = errors
            response_data["total_errors"] = len(errors)

        return JSONResponse(response_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")


# endregion
# ----------------------------
# region --- Chunked Upload


@collections_router.post("/{collection_name}/upload/start")
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

    validate_collection_name(collection_name)
    validate_filename(filename)
    if not replace and not rename:
        await validate_filename_collision(redis_client, collection_name, filename)

    if total_size <= 0:
        raise HTTPException(status_code=400, detail="Total size must be greater than 0")

    if chunk_size <= 0 or chunk_size > 50 * 1024 * 1024:  # Max 50MB per chunk
        raise HTTPException(
            status_code=400, detail="Chunk size must be between 1 byte and 50MB"
        )

    try:
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())

        # Create temp directory for chunks
        temp_dir = Path(settings.UPLOAD_STORAGE_DIR) / "temp" / upload_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Calculate expected number of chunks
        total_chunks = (total_size + chunk_size - 1) // chunk_size

        # Handle duplicate filenames
        if rename:
            collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
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


@collections_router.put("/{collection_name}/upload/{upload_id}")
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


@collections_router.get("/{collection_name}/upload/{upload_id}/status")
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


@collections_router.delete("/{collection_name}/upload/{upload_id}")
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


# Cron job
async def cleanup_expired_uploads(redis_client: redis.Redis):
    """Clean up expired upload sessions."""
    current_time = time.time()

    # Get all upload metadata keys
    upload_keys = [key async for key in redis_client.scan_iter("upload:*:metadata")]

    for key in upload_keys:
        upload_id = key.split(":")[1]

        # Check TTL
        ttl_key = f"upload:{upload_id}:ttl"
        expiry_time = await redis_client.get(ttl_key)

        if expiry_time and float(expiry_time) < current_time:
            # Clean up expired upload
            await cleanup_upload_session(redis_client, upload_id)
            logger.info("Cleaned up expired upload session: %s", upload_id)


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
# region --- Files table


@collections_router.get("")
@collections_router.get("/{collection_name}")
async def get_files(
    collection_name: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort: str | None = "created_at",  # Also set below to cover empty ?sort=
    limit: str = None,
    search: str = None,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Returns files from collections with advanced filtering, sorting, and pagination.

    Args:
        collection_name: Optional collection name. If None, returns files from all collections
        page: Page number (1-based, default: 1)
        page_size: Number of items per page (default: 50, max: 1000)
        sort: Sort field with optional '-' prefix for descending (default: 'created_at')
              Valid fields: filename, size_bytes, created_at, collection_name, file_extension
        limit: Comma-separated list of specific indices to return (e.g., "1,7,12")
        search: Search term to filter by filename or collection name

    Returns:
        JSON response with files and metadata
    """
    if collection_name:
        validate_collection_name(collection_name)

    # Validate and constrain parameters
    page = max(1, page)
    page_size = min(max(1, page_size), 1000)  # Max 1000 items per page

    # Parse limit indices if provided
    limit_indices = []
    if limit:
        try:
            limit_indices = [
                int(idx.strip()) for idx in limit.split(",") if idx.strip().isdigit()
            ]
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail="Invalid limit parameter. Use comma-separated integers.",
            ) from e

    # Validate sort field
    valid_sort_fields = {
        "filename",
        "size_bytes",
        "created_at",
        "collection_name",
        "file_extension",
        "index",
    }

    # Handle empty or None sort parameter
    if not sort or sort.strip() == "":
        sort = "created_at"

    sort_field, sort_descending = _parse_sort_key(sort)
    if sort_field not in valid_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field '{sort_field}'. Valid fields: {', '.join(valid_sort_fields)}",
        )

    try:
        # Determine Redis scan pattern based on collection_name
        if collection_name:
            scan_pattern = f"file_map:{collection_name}/*"
        else:
            scan_pattern = "file_map:*"

        file_keys = [key async for key in redis_client.scan_iter(scan_pattern)]
        print(99999, file_keys)

        # Handle empty results
        if not file_keys:
            if collection_name:
                # Check if collection directory exists but is empty
                collection_dir = Path(settings.UPLOAD_STORAGE_DIR) / collection_name
                if not await run_in_threadpool(collection_dir.is_dir):
                    raise HTTPException(status_code=404, detail="Collection not found.")
                return JSONResponse({"files": []})
            else:
                # No files across all collections
                return JSONResponse(
                    {
                        "files": [],
                        "total_files": 0,
                        "total_collections": 0,
                        "total_size_bytes": 0,
                    }
                )

        # Process all files and add indices
        files = []
        for key in file_keys:
            file_key = key.split(":")[1]
            file_path_str = await redis_client.get(key)
            file_info = await _process_file_info(file_key, file_path_str)
            files.append(file_info)

        # Sort by created_at and add index
        files = _sort_files(files, "created_at", descending=True)
        for idx, file_info in enumerate(files):
            file_info["index"] = idx + 1  # 1-based index

        # Apply search filter first (before sorting/pagination)
        if search:
            files = _filter_files_by_search(files, search)

        # Apply sorting
        files = _sort_files(files, sort_field, sort_descending)

        # Apply limit indices filter (after sorting to maintain index meaning)
        if limit_indices:
            files = _filter_files_by_limit_indices(files, limit_indices)

        # Store total before pagination for metadata
        total_files_after_filters = len(files)

        # Apply pagination
        paginated_files, pagination_info = _paginate_files(files, page, page_size)

        # Prepare response based on whether it's a specific collection or all
        base_response = {"files": paginated_files, "pagination": pagination_info}

        if collection_name:
            # Single collection response
            base_response.update(
                {
                    "collection_name": collection_name,
                    "total_size_bytes": sum(file["size_bytes"] for file in files),
                }
            )
        else:
            # All collections response with additional aggregation
            collections_data = {}
            for (
                file_info
            ) in files:  # Use all files (not paginated) for collection stats
                collection_name_key = file_info["collection_name"]
                if collection_name_key not in collections_data:
                    collections_data[collection_name_key] = {
                        "collection_name": collection_name_key,
                        "file_count": 0,
                        "total_size_bytes": 0,
                    }

                collections_data[collection_name_key]["file_count"] += 1
                collections_data[collection_name_key]["total_size_bytes"] += file_info[
                    "size_bytes"
                ]

            base_response.update(
                {
                    "collections_summary": list(collections_data.values()),
                    "total_collections": len(collections_data),
                    "total_size_bytes": sum(file["size_bytes"] for file in files),
                }
            )

        return JSONResponse(base_response)

    except HTTPException:
        raise
    except Exception as e:
        error_msg = (
            "Error retrieving files from collection"
            if collection_name
            else "Error retrieving all files"
        )
        raise HTTPException(status_code=500, detail=f"{error_msg}: {str(e)}") from e


async def _process_file_info(file_key: str, file_path_str: str | None) -> dict:
    """
    Extract file information from Redis

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

    return {
        "file_key": file_key,
        "filename": filename,
        "collection_name": collection_name,
        "size_bytes": file_size,
        "created_at": created_at,
        "file_extension": file_extension,
    }


def _parse_sort_key(sort_param: str) -> tuple[str, bool]:
    """
    Parse sort parameter to extract field and direction.

    Args:
        sort_param: Sort parameter (e.g., 'filename', '-created_at')

    Returns:
        Tuple of (field_name, is_descending)
    """
    if sort_param.startswith("-"):
        return sort_param[1:], True
    return sort_param, False


def _sort_files(
    files: list[dict], sort_key: str, descending: bool = False
) -> list[dict]:
    """
    Sort files by the specified key.

    Args:
        files: List of file dictionaries
        sort_key: Key to sort by
        descending: Whether to sort in descending order

    Returns:
        Sorted list of files
    """

    # Handle None values for sorting
    def sort_key_func(file_dict):
        value = file_dict.get(sort_key)
        if value is None:
            return "" if isinstance(file_dict.get("filename", ""), str) else 0
        return value

    return sorted(files, key=sort_key_func, reverse=descending)


def _filter_files_by_search(files: list[dict], search_term: str) -> list[dict]:
    """
    Filter files based on search term.

    Args:
        files: List of file dictionaries
        search_term: Search string to match against filename and collection_name

    Returns:
        Filtered list of files
    """
    if not search_term:
        return files

    search_lower = search_term.lower()
    filtered = []

    for file_info in files:
        # Search in filename and collection name
        if (
            search_lower in file_info["filename"].lower()
            or search_lower in file_info["collection_name"].lower()
        ):
            filtered.append(file_info)

    return filtered


def _filter_files_by_limit_indices(
    files: list[dict], limit_indices: list[int]
) -> list[dict]:
    """
    Filter files by specific indices.

    Args:
        files: List of file dictionaries
        limit_indices: List of indices to include

    Returns:
        Filtered list of files
    """
    if not limit_indices:
        return files

    return [file_info for file_info in files if file_info["index"] in limit_indices]


def _paginate_files(
    files: list[dict], page: int, page_size: int
) -> tuple[list[dict], dict]:
    """
    Paginate files and return pagination metadata.

    Args:
        files: List of file dictionaries
        page: Page number (1-based)
        page_size: Number of items per page

    Returns:
        Tuple of (paginated_files, pagination_info)
    """
    total_items = len(files)
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 1

    # Validate page number
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_files = files[start_idx:end_idx]

    pagination_info = {
        "page": page,
        "page_size": page_size,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }

    return paginated_files, pagination_info


# endregion
# ----------------------------
# region --- Download


@collections_router.get("/download/{collection_name}")
async def download_collection(
    collection_name: str,
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """Downloads an entire collection as a ZIP file."""
    validate_collection_name(collection_name)

    try:
        # Get all files in the collection
        file_keys = [
            key async for key in redis_client.scan_iter(f"file_map:{collection_name}/*")
        ]

        if not file_keys:
            raise HTTPException(
                status_code=404, detail="Collection not found or empty."
            )

        # Create a temporary ZIP file
        temp_zip = tempfile.NamedTemporaryFile(
            delete=False, suffix=f"_{collection_name}.zip"
        )

        try:
            with zipfile.ZipFile(temp_zip.name, "w", zipfile.ZIP_DEFLATED) as zip_file:
                files_added = 0

                for key in file_keys:
                    file_path_str = await redis_client.get(key)

                    if file_path_str:
                        file_path = Path(file_path_str)
                        if await run_in_threadpool(file_path.exists):
                            # Security check: ensure the file is within the upload storage directory
                            storage_path = Path(settings.UPLOAD_STORAGE_DIR).resolve()
                            if file_path.resolve().is_relative_to(storage_path):
                                # Get just the filename for the ZIP archive
                                filename = (
                                    file_path.name
                                )  # Add file to ZIP with just the filename (no nested folders in ZIP)
                                await run_in_threadpool(
                                    zip_file.write, str(file_path), filename
                                )
                                files_added += 1
                            else:
                                logger.warning(
                                    "Skipping file outside storage directory: %s",
                                    file_path_str,
                                )
                        else:
                            logger.warning("File not found: %s", file_path_str)

                if files_added == 0:
                    raise HTTPException(
                        status_code=404,
                        detail="No accessible files found in collection.",
                    )

            # Return the ZIP file as a download
            def cleanup_temp_file():
                """Clean up the temporary ZIP file after sending."""
                try:
                    Path(temp_zip.name).unlink()
                except OSError:
                    pass

            return FileResponse(
                path=temp_zip.name,
                media_type="application/zip",
                filename=f"{collection_name}.zip",
                background=BackgroundTask(cleanup_temp_file),
            )

        except Exception as zip_error:
            # Clean up temp file on error
            try:
                Path(temp_zip.name).unlink()
            except OSError:
                pass
            raise zip_error

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating collection archive: {str(e)}"
        ) from e


@collections_router.get("/download/{collection_name}/{filename}")
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
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")


# endregion
# ----------------------------
# region --- Delete


@collections_router.delete("/{collection_name}")
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


@collections_router.delete("/{collection_name}/{filename}")
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
        print("Delete: ", file_key, file_path_str)

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
