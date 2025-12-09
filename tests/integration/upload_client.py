import argparse
import asyncio
import hashlib
import json
import math
import os
import random
import time
from pathlib import Path

import httpx

# ----------------------------
# example usage: python tests/integration/upload_client.py ./testfile.dat my_collection --dummy 50 -v
# ----------------------------


# ----------------------------
# region --- Configuration ---

BASE_URL = "http://localhost:8080"
CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB

# endregion
# ----------------------------
# region --- Main Functions ---


async def upload_file(file_path: Path, collection_name: str, url: str):
    """
    Main function to upload a file with progress and status checks.
    """
    if not file_path.exists():
        _error(f"File not found: {file_path}")
        return

    total_size = file_path.stat().st_size
    total_chunks = math.ceil(total_size / CHUNK_SIZE)
    upload_id = None
    _info(f"Uploading '{file_path.name}' to collection '{collection_name}'...")
    _info(f"Total size: {_format_bytes(total_size)}, Chunk size: {_format_bytes(CHUNK_SIZE)}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. Start upload
            start_url = f"{url}/service/collections/{collection_name}/upload/start"
            start_params = {
                "filename": file_path.name,
                "total_size": total_size,
                "chunk_size": CHUNK_SIZE,
            }
            _verbose("Starting upload...")
            start_resp = await client.post(start_url, params=start_params)
            _handle_error(start_resp)

            upload_id = start_resp.json()["upload_id"]
            _verbose(f"Upload started. ID: {upload_id}")

            # 2. Upload chunks
            await _upload_chunks(
                client, file_path, collection_name, upload_id, url, total_size
            )

            # 3. Poll for completion status
            final_status = await _poll_for_completion(
                client, collection_name, upload_id, url
            )
            _info(f"\nFinal status: {final_status['status']}")
            if final_status["status"] == "completed":
                _success("File upload completed successfully!")
                _verbose(f"File path: {final_status['file_path']}")
                _verbose(f"Checksum (sha256): {final_status['checksum']}")
            else:
                _error(f"Upload failed. Reason: {final_status.get('error', 'Unknown')}")

        except httpx.RequestError as e:
            _error(f"HTTP request failed: {e}")
        except Exception as e:
            _error(f"An unexpected error occurred: {e}")
        finally:
            if upload_id:
                _verbose(f"Upload session ID: {upload_id}")


async def _upload_chunks(
    client: httpx.AsyncClient,
    file_path: Path,
    collection_name: str,
    upload_id: str,
    url: str,
    total_size: int,
):
    """
    Reads the file and uploads it in chunks.
    """
    upload_url = f"{url}/service/collections/{collection_name}/upload/{upload_id}"
    chunk_num = 0
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            start_byte = chunk_num * CHUNK_SIZE
            end_byte = start_byte + len(chunk) - 1
            headers = {"Content-Range": f"bytes {start_byte}-{end_byte}/{total_size}"}

            _progress_bar(end_byte + 1, total_size, prefix="Uploading:")
            upload_resp = await client.put(upload_url, content=chunk, headers=headers)
            _handle_error(upload_resp)
            chunk_num += 1


async def _poll_for_completion(
    client: httpx.AsyncClient, collection_name: str, upload_id: str, url: str
) -> dict:
    """
    Polls the status endpoint until the file is assembled.
    """
    status_url = f"{url}/service/collections/{collection_name}/upload/{upload_id}/status"
    _info("\nWaiting for file to be assembled...")
    while True:
        status_resp = await client.get(status_url)
        _handle_error(status_resp)
        status_data = status_resp.json()
        if status_data["status"] in ["completed", "failed"]:
            return status_data
        await asyncio.sleep(1)


# endregion
# ----------------------------
# region --- Helpers & CLI ---


def _handle_error(response: httpx.Response):
    """
    Raises an exception if the response indicates an error.
    """
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except json.JSONDecodeError:
            detail = response.text
        raise Exception(
            f"API Error: {response.status_code} {response.reason_phrase} - {detail}"
        )


def _progress_bar(
    iteration, total, prefix="", suffix="", decimals=1, length=50, fill="█"
):
    """
    Creates and prints a terminal progress bar.
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end="\r")
    if iteration == total:
        print()


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
    print(f"\x1b[34m[INFO]\x1b[0m {msg}")


def _verbose(msg):
    if ARGS.verbose:
        print(f"\x1b[37m[VERBOSE]\x1b[0m {msg}")


def _success(msg):
    print(f"\x1b[32m[SUCCESS]\x1b[0m {msg}")


def _error(msg):
    print(f"\x1b[31m[ERROR]\x1b[0m {msg}")


def _create_dummy_file(file_path: Path, size_mb: int) -> None:
    """Creates a dummy file of a given size."""
    _info(f"Creating a dummy file of {size_mb} MB at '{file_path}'...")
    with open(file_path, "wb") as f:
        f.write(os.urandom(size_mb * 1024 * 1024))
    _success(f"Dummy file created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunked file upload test client.")
    parser.add_argument("file_path", help="Path to the file to upload.")
    parser.add_argument(
        "collection_name", help="Name of the collection to upload the file to."
    )
    parser.add_argument(
        "--url", default=BASE_URL, help=f"Base URL of the service. Default: {BASE_URL}"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output."
    )
    parser.add_argument(
        "--dummy",
        type=int,
        metavar="SIZE_MB",
        help="Create a dummy file of SIZE_MB megabytes at the specified file_path before uploading.",
    )
    ARGS = parser.parse_args()

    file_path = Path(ARGS.file_path)

    if ARGS.dummy:
        _create_dummy_file(file_path, ARGS.dummy)

    asyncio.run(upload_file(file_path, ARGS.collection_name, ARGS.url))

# endregion
