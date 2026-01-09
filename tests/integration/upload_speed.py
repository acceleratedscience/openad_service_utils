# pylint: disable=broad-exception-raised
# pylint: disable=broad-exception-caught

import os
import math
import time
import httpx
import asyncio
import argparse
from pathlib import Path

# ----------------------------
# Test for benchmarking the server's upload speed.
#
# Example usage:
# python tests/integration/upload_speed.py ./testfile.dat my_collection --dummy 50 -v --token abc123
# python tests/integration/upload_speed.py ./testfile.dat my_collection --dummy 50 -v --local
# ----------------------------


# ----------------------------
# region --- Configuration

PROD_URL = "https://open.accelerate.science/proxy"
LOCAL_URL = "http://localhost:8080"
VERBOSE = False

# endregion
# ----------------------------
# region --- Main Functions


async def upload_file(file_path: Path, collection_name: str, token: str, local: bool):
    """
    Uploads a single file to the specified collection to test upload speed.
    Uses the direct upload endpoint (POST /service/collections/{collection_name}).
    """
    if not file_path.exists():
        _error(f"File not found: {file_path}")
        return

    # Determine Base URL and Headers
    if local:
        base_url = LOCAL_URL
        headers = {}
        _info(f"Running in LOCAL mode against {base_url}")
    else:
        base_url = PROD_URL
        if not token:
            _error("Token is required for production usage. Use --token <token>.")
            return
        headers = {
            "Inference-Service": "neural-pde-solvers",
            "Authorization": f"Bearer {token}",
        }
        _info(f"Running in PRODUCTION mode against {base_url}")

    # Construct full URL
    url = f"{base_url}/service/collections/{collection_name}"

    file_size = file_path.stat().st_size
    _info(f"Uploading '{file_path.name}' to '{url}'...")
    _info(f"File size: {_format_bytes(file_size)}")

    # Disable timeout for large uploads as this is a speed test
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            start_time = time.time()

            # Open file in binary mode and upload
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f)}

                _verbose("Sending request...")
                response = await client.post(url, files=files, headers=headers)

            end_time = time.time()
            duration = end_time - start_time

            _handle_error(response)

            _success("\x1b[32mUpload completed successfully\x1b[0m")
            _info(f"\x1b[33mTime taken: {duration:.2f} seconds\x1b[0m")

            if duration > 0:
                speed = file_size / duration
                _info(f"Average Speed: {_format_bytes(speed)}/s")

            _verbose(f"Response: {response.json()}")

        except httpx.RequestError as e:
            _error(f"HTTP request failed: {e}")
        except Exception as e:
            _error(f"An unexpected error occurred: {e}")


# endregion
# ----------------------------
# region --- Helpers & CLI


def _handle_error(response: httpx.Response):
    """
    Raises an exception if the response indicates an error.
    """
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise Exception(
            f"API Error: {response.status_code} {response.reason_phrase} - {detail}"
        )


def _format_bytes(size_bytes):
    """
    Formats a byte size into a human-readable string.
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def _info(msg):
    print(f"\x1b[34m{'[INFO]':<9}\x1b[0m {msg}")


def _verbose(msg):
    if VERBOSE:
        print(f"\x1b[37m{'[VERBOSE]':<9}\x1b[0m {msg}")


def _success(msg):
    print(f"\x1b[32m{'[SUCCESS]':<9}\x1b[0m {msg}")


def _error(msg):
    print(f"\x1b[31m{'[ERROR]':<9}\x1b[0m {msg}")


def _create_dummy_file(file_path: Path, size_mb: int) -> None:
    """Creates a dummy file of a given size."""
    _info(f"Creating a dummy file of {size_mb} MB at '{file_path}'...")
    with open(file_path, "wb") as f:
        f.write(os.urandom(size_mb * 1024 * 1024))
    _success("Dummy file created")


# endregion
# ----------------------------
# region --- Evocation

if __name__ == "__main__":
    # fmt: off
    parser = argparse.ArgumentParser(description="Single file upload speed test client.")
    parser.add_argument("file_path", help="Path to the file to upload.")
    parser.add_argument("collection_name", help="Name of the collection to upload the file to.")
    parser.add_argument("--token", help="Authorization token (required for production).")
    parser.add_argument("--local", action="store_true", help="Use local URL instead of production proxy.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("--dummy", type=int, metavar="SIZE_MB", help="Create a dummy file of SIZE_MB megabytes at the specified file_path before uploading.")
    # fmt: on

    ARGS = parser.parse_args()
    VERBOSE = ARGS.verbose
    file_path = Path(ARGS.file_path)

    if ARGS.dummy:
        _create_dummy_file(file_path, ARGS.dummy)

    asyncio.run(upload_file(file_path, ARGS.collection_name, ARGS.token, ARGS.local))

# endregion
