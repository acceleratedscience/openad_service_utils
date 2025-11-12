"""
Helper functions for validating API inputs
"""

# Std
import re

# 3rd Party
import redis.asyncio as redis
from fastapi import HTTPException


def validate_collection_name(collection_name: str):
    """Validates the collection name for prohibited characters."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", collection_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid collection name. Only alphanumeric characters, underscores and hyphens allowed.",
        )


def validate_filename(filename: str):
    """Validates the filename for problematic characters."""
    sanitized_filename = re.sub(r'[<>:"/\\|?*]', "-", filename)
    if filename != sanitized_filename:
        raise HTTPException(status_code=422, detail="Invalid filename")


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
            detail=f"File '{filename}' already exists in collection '{collection_name}'",
        )
