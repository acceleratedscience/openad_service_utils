# ----------------------------
# region --- Setup

# UPLOAD_STORAGE_DIR = ~/.openad_models/collection_uploads

# Std
import time
import uuid
import json
import shutil
import random
import asyncio
import logging
import zipfile
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta


# 3rd Party
import redis.asyncio as redis
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.background import BackgroundTask
from fastapi import APIRouter, Depends, File, Body
from fastapi import HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

# Schemas
from openad_service_utils.api.models import FileInfo

# Utils
from openad_service_utils.utils.router_dependencies import get_redis_client
from openad_service_utils.api.config import get_config_instance
from openad_service_utils.utils.validation import (
    validate_collection_name,
    validate_filename,
    validate_filename_collision,
)

# Get configuration and logger
settings = get_config_instance()
logger = logging.getLogger(__name__)


jobs_router = APIRouter(
    prefix="/service/pde/jobs",
    # tags=["ALL JOB ROUTES"],
)

# endregion
# ----------------------------
# region --- System routes


@jobs_router.get(
    "/model-versions",
    summary="Get model versions to populate dropdown",
    tags=["Data for UI"],
)
async def get_model_versions(redis_client: redis.Redis = Depends(get_redis_client)):
    """Returns a list of all available model versions."""
    try:
        versions = ["v1.0", "v1.1", "v2.0", "v2.1", "v3.0"]  # FPO
        return JSONResponse({"versions": versions})
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving model versions: {str(e)}"
        ) from e


# endregion
# ----------------------------
# region --- Create


class CreateJobRequest(BaseModel):
    collection_name: str | None = None
    files: list[FileInfo] | None = None


@jobs_router.post("/create/{job_name}", summary="Create a new job", tags=["Jobs"])
async def create_job(request_data: CreateJobRequest):
    """
    Create a new job.
    Takes either a collection name or a list of files.

    Args:
        collection_name (str): Name of the collection to create the job for.
        files (List[FileInfo]): List of files to include in the job.
        redis_client (redis.Redis): Redis client dependency.

    """
    try:
        if request_data.collection_name:
            print(f"Creating job in collection: {request_data.collection_name}")
        elif request_data.files:
            print(f"Creating job with files: {request_data.files}")
        else:
            raise HTTPException(
                status_code=400, detail="No collection or files provided."
            )

        raise NotImplementedError("Not yet implemented")
        return JSONResponse({"success": True})
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating job: {str(e)}"
        ) from e


# endregion
# ----------------------------
