#
# MIT License
#
# Copyright (c) 2022 GT4SD team
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
"""Module configuration."""

import logging
import os
from functools import lru_cache
from typing import Dict, Optional, Set

from pydantic_settings import BaseSettings
from openad_service_utils.utils.logging_config import setup_logging
from openad_service_utils.common.s3 import GT4SDS3Client, S3SyncError, sync_folder_with_s3, upload_file_to_s3

# Set up logging configuration
setup_logging()

# Create a logger
logger = logging.getLogger(__name__)


class GT4SD_DEFAULTS:
    GT4SD_S3_HOST: str = "s3.par01.cloud-object-storage.appdomain.cloud"

class GT4SDConfiguration(BaseSettings):
    """GT4SDConfiguration settings from environment variables.

    Default configurations for gt4sd including a read-only COS for algorithms' artifacts.
    Default configuration for gt4sd hub including a read-write COS for algorithms' artifacts uploaded by users.
    """

    # reimplemented .gt4sd to .openad_models
    gt4sd_local_cache_path: str = os.path.join(os.path.expanduser("~"), ".openad_models")
    gt4sd_local_cache_path_algorithms: str = "algorithms"
    gt4sd_local_cache_path_properties: str = "properties"
    gt4sd_max_number_of_stuck_calls: int = 50
    gt4sd_max_number_of_samples: int = 1000000
    gt4sd_max_runtime: int = 86400
    gt4sd_create_unverified_ssl_context: bool = False
    gt4sd_disable_cudnn: bool = False

    ACCESS_KEY_ID_NAME: str = "AWS_ACCESS_KEY_ID"
    SECRET_ACCESS_KEY_NAME: str = "AWS_SECRET_ACCESS_KEY"

    # use environment variables for private cos buckets or default to public buckets
    OPENAD_S3_HOST: str = os.getenv(
        "GT4SD_S3_HOST", "s3.par01.cloud-object-storage.appdomain.cloud"
    )
    OPENAD_S3_ACCESS_KEY: str = os.getenv(
        ACCESS_KEY_ID_NAME, "6e9891531d724da89997575a65f4592e"
    )
    OPENAD_S3_SECRET_KEY: str = os.getenv(
        SECRET_ACCESS_KEY_NAME, "5997d63c4002cc04e13c03dc0c2db9dae751293dab106ac5"
    )
    OPENAD_S3_SECURE: bool | str = os.getenv("GT4SD_S3_SECURE", True)
    OPENAD_S3_BUCKET_ALGORITHMS: str = os.getenv(
        "GT4SD_S3_BUCKET_ALGORITHMS", "gt4sd-cos-algorithms-artifacts"
    )
    OPENAD_S3_BUCKET_PROPERTIES: str = os.getenv(
        "GT4SD_S3_BUCKET_PROPERTIES", "gt4sd-cos-properties-artifacts"
    )

    # use environment variables for private cos hub buckets or default to public buckets
    OPENAD_S3_HOST_HUB: str = os.getenv(
        "GT4SD_S3_HOST_HUB", "s3.par01.cloud-object-storage.appdomain.cloud"
    )
    OPENAD_S3_ACCESS_KEY_HUB: str = os.getenv(
        ACCESS_KEY_ID_NAME, "d9536662ebcf462f937efb9f58012830"
    )
    OPENAD_S3_SECRET_KEY_HUB: str = os.getenv(
        SECRET_ACCESS_KEY_NAME, "934d1f3afdaea55ac586f6c2f729ac2ba2694bb8e975ee0b"
    )
    OPENAD_S3_SECURE_HUB: bool | str = os.getenv("GT4SD_S3_SECURE_HUB", True)
    OPENAD_S3_BUCKET_HUB_ALGORITHMS: str = os.getenv(
        "GT4SD_S3_BUCKET_HUB_ALGORITHMS", "gt4sd-cos-hub-algorithms-artifacts"
    )
    OPENAD_S3_BUCKET_HUB_PROPERTIES: str = os.getenv(
        "GT4SD_S3_BUCKET_HUB_PROPERTIES", "gt4sd-cos-hub-properties-artifacts"
    )

    class Config:
        # immutable and in turn hashable, that is required for lru_cache
        frozen = True

    @staticmethod
    @lru_cache(maxsize=None)
    def get_instance() -> "GT4SDConfiguration":
        return GT4SDConfiguration()


class GT4SDArtifactManagementConfiguration:
    """Artifact management configuration."""

    gt4sd_s3_modules: Set[str] = {"algorithms", "properties"}

    def __init__(self, gt4sd_configuration: GT4SDConfiguration) -> None:
        """Initialize the artifact management configuration from the base one.

        Args:
            gt4sd_configuration: GT4SD base configuration.
        """
        self.local_cache_path: Dict[str, str] = {
            "algorithms": gt4sd_configuration.gt4sd_local_cache_path_algorithms,
            "properties": gt4sd_configuration.gt4sd_local_cache_path_properties,
        }
        self.s3_bucket: Dict[str, str] = {
            "algorithms": gt4sd_configuration.OPENAD_S3_BUCKET_ALGORITHMS,
            "properties": gt4sd_configuration.OPENAD_S3_BUCKET_PROPERTIES,
        }
        self.s3_bucket_hub: Dict[str, str] = {
            "algorithms": gt4sd_configuration.OPENAD_S3_BUCKET_HUB_ALGORITHMS,
            "properties": gt4sd_configuration.OPENAD_S3_BUCKET_HUB_PROPERTIES,
        }


gt4sd_configuration_instance = GT4SDConfiguration.get_instance()
gt4sd_artifact_management_configuration = GT4SDArtifactManagementConfiguration(
    gt4sd_configuration=gt4sd_configuration_instance
)

for key, val in gt4sd_artifact_management_configuration.local_cache_path.items():
    # logger.info(f"using as local cache path for {key}: {val}")
    path = os.path.join(gt4sd_configuration_instance.gt4sd_local_cache_path, val)
    try:
        os.makedirs(path)
    except FileExistsError:
        pass
        # logger.debug(f"local cache path for {key} already exists at {path}.")


def upload_to_s3(target_filepath: str, source_filepath: str, module: str = "algorithms"):
    """Upload an algorithm in source_filepath in target_filepath on a bucket in the model hub.
    Args:
        target_filepath: path to save the objects in s3.
        source_filepath: path to the file to sync.
        module: the submodule of gt4sd that acts as a root for the bucket, defaults
            to `algorithms`.
    """

    if module not in gt4sd_artifact_management_configuration.gt4sd_s3_modules:
        raise ValueError(
            f"Unknown cache module: {module}. Supported modules: "
            f"{','.join(gt4sd_artifact_management_configuration.gt4sd_s3_modules)}"
        )

    try:
        upload_file_to_s3(
            host=gt4sd_configuration_instance.OPENAD_S3_HOST_HUB,
            access_key=gt4sd_configuration_instance.OPENAD_S3_ACCESS_KEY_HUB,
            secret_key=gt4sd_configuration_instance.OPENAD_S3_SECRET_KEY_HUB,
            bucket=gt4sd_artifact_management_configuration.s3_bucket_hub[module],
            target_filepath=target_filepath,
            source_filepath=source_filepath,
            secure=gt4sd_configuration_instance.OPENAD_S3_SECURE_HUB,
        )
    except S3SyncError:
        logger.exception("error in syncing the cache with S3")


def sync_algorithm_with_s3(prefix: Optional[str] = None, module: str = "algorithms") -> str:
    """Sync an algorithm in the local cache using environment variables.

    Args:
        prefix: the relative path in the bucket (both
            on S3 and locally) to match files to download. Defaults to None.
        module: the submodule of gt4sd that acts as a root for the bucket, defaults
            to `algorithms`.

    Returns:
        str: local path using the prefix.
    """
    if module not in gt4sd_artifact_management_configuration.gt4sd_s3_modules:
        raise ValueError(
            f"Unknown cache module: {module}. Supported modules: "
            f"{','.join(gt4sd_artifact_management_configuration.gt4sd_s3_modules)}"
        )

    folder_path = os.path.join(
        gt4sd_configuration_instance.gt4sd_local_cache_path,
        gt4sd_artifact_management_configuration.local_cache_path[module],
    )

    try:
        # sync with the public bucket
        sync_folder_with_s3(
            host=gt4sd_configuration_instance.OPENAD_S3_HOST,
            access_key=gt4sd_configuration_instance.OPENAD_S3_ACCESS_KEY,
            secret_key=gt4sd_configuration_instance.OPENAD_S3_SECRET_KEY,
            bucket=gt4sd_artifact_management_configuration.s3_bucket[module],
            folder_path=folder_path,
            prefix=prefix,
            secure=gt4sd_configuration_instance.OPENAD_S3_SECURE,
        )
        # sync with the public bucket hub
        sync_folder_with_s3(
            host=gt4sd_configuration_instance.OPENAD_S3_HOST_HUB,
            access_key=gt4sd_configuration_instance.OPENAD_S3_ACCESS_KEY_HUB,
            secret_key=gt4sd_configuration_instance.OPENAD_S3_SECRET_KEY_HUB,
            bucket=gt4sd_artifact_management_configuration.s3_bucket_hub[module],
            folder_path=folder_path,
            prefix=prefix,
            secure=gt4sd_configuration_instance.OPENAD_S3_SECURE_HUB,
        )
    except S3SyncError:
        logger.exception("error in syncing the cache with S3")
        raise
    return os.path.join(folder_path, prefix) if prefix is not None else folder_path


def get_cached_algorithm_path(prefix: Optional[str] = None, module: str = "algorithms") -> str:
    if module not in gt4sd_artifact_management_configuration.gt4sd_s3_modules:
        raise ValueError(
            f"Unknown cache module: {module}. Supported modules: "
            f"{','.join(gt4sd_artifact_management_configuration.gt4sd_s3_modules)}."
        )

    return (
        os.path.join(
            gt4sd_configuration_instance.gt4sd_local_cache_path,
            gt4sd_artifact_management_configuration.local_cache_path[module],
            prefix,
        )
        if prefix is not None
        else os.path.join(
            gt4sd_configuration_instance.gt4sd_local_cache_path,
            gt4sd_artifact_management_configuration.local_cache_path[module],
        )
    )


def get_algorithm_subdirectories_from_s3_coordinates(
    host: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    secure: bool = True,
    prefix: Optional[str] = None,
) -> Set[str]:
    """Wrapper to initialize a client and list the directories in a bucket."""
    client = GT4SDS3Client(host=host, access_key=access_key, secret_key=secret_key, secure=secure)
    return client.list_directories(bucket=bucket, prefix=prefix)


def get_algorithm_subdirectories_with_s3(prefix: Optional[str] = None, module: str = "algorithms") -> Set[str]:
    """Get algorithms in the s3 buckets.

    Args:
        prefix: the relative path in the bucket (both
            on S3 and locally) to match files to download. Defaults to None.
        module: the submodule of gt4sd that acts as a root for the bucket, defaults
            to `algorithms`.

    Returns:
        Set: set of available algorithms on s3 with that prefix.
    """
    if module not in gt4sd_artifact_management_configuration.gt4sd_s3_modules:
        raise ValueError(
            f"Unknown cache module: {module}. Supported modules: "
            f"{','.join(gt4sd_artifact_management_configuration.gt4sd_s3_modules)}"
        )

    try:
        # directories in the read-only public bucket
        dirs = get_algorithm_subdirectories_from_s3_coordinates(
            host=gt4sd_configuration_instance.OPENAD_S3_HOST,
            access_key=gt4sd_configuration_instance.OPENAD_S3_ACCESS_KEY,
            secret_key=gt4sd_configuration_instance.OPENAD_S3_SECRET_KEY,
            bucket=gt4sd_artifact_management_configuration.s3_bucket[module],
            secure=gt4sd_configuration_instance.OPENAD_S3_SECURE,
            prefix=prefix,
        )

        # directories in the write public-hub bucket
        dirs_hub = get_algorithm_subdirectories_from_s3_coordinates(
            host=gt4sd_configuration_instance.OPENAD_S3_HOST_HUB,
            access_key=gt4sd_configuration_instance.OPENAD_S3_ACCESS_KEY_HUB,
            secret_key=gt4sd_configuration_instance.OPENAD_S3_SECRET_KEY_HUB,
            bucket=gt4sd_artifact_management_configuration.s3_bucket_hub[module],
            secure=gt4sd_configuration_instance.OPENAD_S3_SECURE_HUB,
            prefix=prefix,
        )

        # set of directories in the public bucket and public hub bucket
        versions = dirs.union(dirs_hub)
        return versions

    except Exception:
        logger.exception("generic syncing error")
        raise S3SyncError(
            "CacheSyncingError",
            f"error in getting directories of prefix={prefix}",
        )


def get_algorithm_subdirectories_in_cache(prefix: Optional[str] = None, module: str = "algorithms") -> Set[str]:
    """Get algorithm subdirectories from the cache.

    Args:
        prefix: prefix matching cache subdirectories. Defaults to None.
        module: the submodule of gt4sd that acts as a root for the bucket, defaults
            to `algorithms`.

    Returns:
        a set of subdirectories.
    """
    path = get_cached_algorithm_path(prefix=prefix, module=module)
    try:
        _, dirs, _ = next(iter(os.walk(path)))
        return set(dirs)
    except StopIteration:
        return set()


def reset_logging_root_logger():
    """Reset the root logger from logging library."""
    root = logging.getLogger()
    root.handlers = []
    root.filters = []

if __name__ == "__main__":
    c = GT4SDConfiguration()
    for i in c:
        print(i)
