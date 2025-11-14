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


results_router = APIRouter(
    prefix="/service/pde/results",
    # tags=["ALL JOB RESULT ROUTES"],
)

# endregion
# ----------------------------
# region --- System routes


# endregion
# ----------------------------
# region --- Create


# endregion
# ----------------------------
