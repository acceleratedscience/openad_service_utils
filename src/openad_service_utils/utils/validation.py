"""
Helper functions for validating API inputs
"""

import re
from fastapi import HTTPException


def validate_collection_name(collection_name: str):
    """Validates the collection name to be alphanumeric with underscores and hyphens."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", collection_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid collection name. Only alphanumeric characters, underscores, and hyphens are allowed.",
        )


def validate_filename(filename: str):
    """Validates the filename to prevent directory traversal."""
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
