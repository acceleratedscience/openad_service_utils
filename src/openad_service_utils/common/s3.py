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
"""S3 storage utilities."""

import logging
import os
from contextlib import contextmanager
from typing import Generator, List, Optional, Set
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error
from tenacity import retry, stop_after_attempt, wait_exponential

from .exceptions import S3SyncError
from openad_service_utils.utils.logging_config import setup_logging

# Set up logging configuration
setup_logging()

# Create a logger
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
CHUNK_SIZE = 65536  # 64KB chunks for multipart upload
VALID_BUCKET_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789-.")


class GT4SDS3Client:
    def __init__(
        self, host: str, access_key: Optional[str] = None, secret_key: Optional[str] = None, secure: bool = True
    ) -> None:
        """
        Construct an S3 client.

        Args:
            host: s3 host address.
            access_key: s3 access key. Optional for anonymous access.
            secret_key: s3 secret key. Optional for anonymous access.
            secure: whether the connection is secure or not. Defaults to True.

        Raises:
            ValueError: If host is invalid or if only one credential is provided.
        """
        if not host or not isinstance(host, str):
            raise ValueError("Invalid host address")

        self.host = host
        self.secure = secure

        # Handle anonymous access if both credentials are None/empty
        self.is_anonymous = (access_key is None or access_key == "") and (secret_key is None or secret_key == "")

        if self.is_anonymous:
            self.access_key = ""
            self.secret_key = ""
            logger.info("Using anonymous access mode")
        else:
            # Validate credentials if not anonymous
            if bool(access_key) != bool(secret_key):  # XOR check
                raise ValueError("Both access_key and secret_key must be provided or neither")
            if not isinstance(access_key, str) or not isinstance(secret_key, str):
                raise ValueError("Invalid access_key or secret_key type")
            self.access_key = access_key
            self.secret_key = secret_key

        self.client = Minio(
            self.host,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    @staticmethod
    def validate_bucket_name(bucket: str) -> None:
        """
        Validate S3 bucket name according to naming rules.

        Args:
            bucket: The bucket name to validate.

        Raises:
            ValueError: If bucket name is invalid.
        """
        if not bucket or not isinstance(bucket, str):
            raise ValueError("Bucket name must be a non-empty string")
        if len(bucket) < 3 or len(bucket) > 63:
            raise ValueError("Bucket name must be between 3 and 63 characters")
        if not all(c in VALID_BUCKET_CHARS for c in bucket.lower()):
            raise ValueError("Bucket name contains invalid characters")
        if bucket.startswith("-") or bucket.endswith("-"):
            raise ValueError("Bucket name cannot start or end with a hyphen")

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    def list_bucket_names(self) -> List[str]:
        """
        List all available s3 bucket names.

        Returns:
             List[str]: list with bucket names.

        Raises:
            S3Error: If there's an error accessing S3.
        """
        try:
            return [bucket.name for bucket in self.client.list_buckets()]
        except S3Error as e:
            logger.error(f"Failed to list buckets: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    def list_object_names(self, bucket: str, prefix: Optional[str] = None) -> List[str]:
        """
        List all available objects (recursive) in the given bucket based on a given prefix.

        Args:
            bucket: bucket name to search for objects.
            prefix: prefix for objects in the bucket.
                Defaults to None, a.k.a., no prefix filter.

        Returns:
            List[str]: list with object names.

        Raises:
            ValueError: If bucket name is invalid.
            S3Error: If there's an error accessing S3.
        """
        self.validate_bucket_name(bucket)
        try:
            return [
                s3_object.object_name
                for s3_object in self.client.list_objects(bucket_name=bucket, prefix=prefix, recursive=True)
            ]
        except S3Error as e:
            logger.error(f"Failed to list objects in bucket {bucket}: {str(e)}")
            raise

    def check_prefix_exists(self, bucket: str, prefix: str) -> bool:
        """
        Check if a prefix exists in the given bucket.

        Args:
            bucket: bucket name to search for objects.
            prefix: prefix to check for existence.

        Returns:
            bool: True if prefix exists, False otherwise.

        Raises:
            ValueError: If bucket name is invalid or prefix is empty.
            S3Error: If there's an error accessing S3.
        """
        if not prefix:
            raise ValueError("Prefix cannot be empty")

        self.validate_bucket_name(bucket)
        try:
            # Normalize prefix to ensure consistent checking
            normalized_prefix = prefix.rstrip("/") + "/"
            objects = self.client.list_objects(bucket_name=bucket, prefix=normalized_prefix, recursive=False)
            # Check if there are any objects with this prefix
            return any(True for _ in objects)
        except S3Error as e:
            logger.error(f"Failed to check prefix in bucket {bucket}: {str(e)}")
            raise

    def ensure_prefix_exists(self, bucket: str, prefix: str) -> None:
        """
        Ensure a prefix exists in the given bucket, throwing an error if it doesn't.

        Args:
            bucket: bucket name to search for objects.
            prefix: prefix that must exist.

        Raises:
            ValueError: If bucket name is invalid, prefix is empty, or prefix doesn't exist.
            S3Error: If there's an error accessing S3.
        """
        if not self.check_prefix_exists(bucket, prefix):
            logger.error(f"Prefix Path '{prefix}' does not exist in bucket '{bucket}'")
            raise ValueError(f"Prefix Path '{prefix}' does not exist in bucket '{bucket}'")

    def list_directories(self, bucket: str, prefix: Optional[str] = None) -> Set[str]:
        """
        List all available "directories" in the given bucket based on a given prefix.

        Args:
            bucket: bucket name to search for objects.
            prefix: prefix for objects in the bucket.
                Defaults to None, a.k.a., no prefix filter.
                Needs to be a "directory" itself.

        Returns:
            Set[str]: set with directory names.

        Raises:
            ValueError: If bucket name is invalid.
            S3Error: If there's an error accessing S3.
        """
        self.validate_bucket_name(bucket)
        if prefix:
            prefix = prefix + "/" if prefix[-1] != "/" else prefix
        try:
            return set(
                s3_object.object_name[len(prefix) if prefix else 0 : -1]
                for s3_object in self.client.list_objects(bucket_name=bucket, prefix=prefix, recursive=False)
                if s3_object.object_name[-1] == "/"
            )
        except S3Error as e:
            logger.error(f"Failed to list directories in bucket {bucket}: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10), reraise=True)
    def upload_file(self, bucket: str, target_filepath: str, source_filepath: str) -> None:
        """Upload a local file to S3 bucket.

        Args:
            bucket: bucket name to upload to.
            target_filepath: path to the file in S3.
            source_filepath: path to the file to upload.

        Raises:
            ValueError: If bucket name is invalid or file doesn't exist.
            S3Error: If there's an error uploading to S3.
            PermissionError: If anonymous access is used (write operations not allowed).
        """
        if self.is_anonymous:
            raise PermissionError("Upload operations not allowed with anonymous access")

        self.validate_bucket_name(bucket)
        if not os.path.exists(source_filepath):
            raise ValueError(f"Source file does not exist: {source_filepath}")

        try:
            file_size = os.path.getsize(source_filepath)
            if file_size > CHUNK_SIZE:
                # Use multipart upload for large files
                self.client.fput_object(bucket, target_filepath, source_filepath, part_size=CHUNK_SIZE)
            else:
                self.client.fput_object(bucket, target_filepath, source_filepath)
        except S3Error as e:
            logger.error(f"Failed to upload file {source_filepath}: {str(e)}")
            raise

    def sync_folder(self, bucket: str, path: str, prefix: Optional[str] = None, force: bool = False) -> None:
        """Sync an entire folder from S3 recursively and save it under the given path.

        If :obj:`prefix` is given, every file under ``prefix/`` in S3 will be saved under ``path/`` in disk (i.e.
        ``prefix/`` is replaced by ``path/``).

        Args:
            bucket: bucket name to search for objects.
            path: path to save the objects in disk.
            prefix: prefix for objects in the bucket. Defaults to None, a.k.a., no prefix filter.
            force: force download even if a file with the same name is present. Defaults to False.

        Raises:
            ValueError: If bucket name is invalid.
            S3Error: If there's an error accessing S3.
            OSError: If there's an error creating directories or writing files.
        """
        self.ensure_prefix_exists(bucket, prefix=prefix)

        if not os.path.exists(path):
            logger.warning(f"path {path} does not exist, creating it...")
            os.makedirs(path)

        try:
            s3_objects = self.client.list_objects(bucket_name=bucket, prefix=prefix, recursive=True)

            for s3_object in s3_objects:
                object_name = s3_object.object_name
                is_directory = object_name.endswith("/")

                object_name_stripped_prefix = os.path.relpath(object_name, prefix) if prefix else object_name

                filepath = os.path.join(
                    path, object_name_stripped_prefix[1:] if object_name[0] == "/" else object_name_stripped_prefix
                )

                if is_directory:
                    if not os.path.isdir(filepath):
                        os.makedirs(filepath)
                        logger.debug(f"creating empty directory: '{filepath}'")
                    continue

                # Create parent directories for file if they don't exist
                parent_dir = os.path.dirname(filepath)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                # Check if download is needed
                if not os.path.exists(filepath) or force:
                    logger.debug(f"downloading file '{os.path.basename(object_name)}' to '{filepath}'")
                    try:
                        self.client.fget_object(bucket_name=bucket, object_name=object_name, file_path=filepath)
                    except S3Error as e:
                        logger.error(f"Failed to download {object_name}: {str(e)}")
                        raise

        except S3Error as e:
            logger.error(f"Failed to sync folder from bucket {bucket}: {str(e)}")
            raise


@contextmanager
def s3_client(
    host: str, access_key: Optional[str] = None, secret_key: Optional[str] = None, secure: bool = True
) -> Generator[GT4SDS3Client, None, None]:
    """
    Context manager for S3 client to ensure proper resource cleanup.

    Args:
        host: s3 host address.
        access_key: s3 access key. Optional for anonymous access.
        secret_key: s3 secret key. Optional for anonymous access.
        secure: whether the connection is secure or not.

    Yields:
        GT4SDS3Client: The S3 client instance.
    """
    client = GT4SDS3Client(host=host, access_key=access_key, secret_key=secret_key, secure=secure)
    try:
        yield client
    finally:
        # Clean up any resources if needed
        pass


def upload_file_to_s3(
    host: str,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    bucket: str = "",
    target_filepath: str = "",
    source_filepath: str = "",
    secure: bool = True,
) -> None:
    """
    Upload a file to S3 storage.

    Args:
        host: s3 host address.
        access_key: s3 access key. Optional for anonymous access.
        secret_key: s3 secret key. Optional for anonymous access.
        bucket: bucket name to search for objects.
        target_filepath: path to save the objects in s3.
        source_filepath: path to the file to sync.
        secure: whether the connection is secure or not. Defaults to True.

    Raises:
        S3SyncError: in case of S3 syncing errors.
        PermissionError: If anonymous access is used (write operations not allowed).
    """
    try:
        with s3_client(host=host, access_key=access_key, secret_key=secret_key, secure=secure) as client:
            logger.debug("starting upload")
            client.upload_file(bucket, target_filepath, source_filepath)
            logger.debug("upload complete")
    except (ValueError, S3Error, PermissionError) as e:
        logger.exception("upload error " + f"Error uploading file to S3: {str(e)}")
        raise S3SyncError("UploadArtifactsError", f"Error uploading file to S3: {str(e)}")


def sync_folder_with_s3(
    host: str,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    bucket: str = "",
    folder_path: str = "",
    prefix: Optional[str] = None,
    secure: bool = True,
) -> None:
    """
    Sync a folder with S3 remote storage.

    Args:
        host: s3 host address.
        access_key: s3 access key. Optional for anonymous access.
        secret_key: s3 secret key. Optional for anonymous access.
        bucket: bucket name to search for objects.
        folder_path: folder path.
        prefix: prefix for objects in the bucket. Defaults to None, a.k.a., no prefix filter.
        secure: whether the connection is secure or not. Defaults to True.

    Raises:
        S3SyncError: in case of S3 syncing errors.
    """
    path = os.path.join(folder_path, prefix) if prefix else folder_path
    logger.info(f"using host={host} bucket={bucket} path={path}")

    try:
        with s3_client(host=host, access_key=access_key, secret_key=secret_key, secure=secure) as client:
            logger.info("starting sync")
            client.sync_folder(bucket=bucket, path=path, prefix=prefix)
            logger.info("sync complete. artifacts downloaded.")
    except (ValueError, S3Error, OSError) as e:
        logger.exception(f"S3 sync error {str(e)}")
        # raise
        raise S3SyncError("CacheSyncingError", f"Error syncing with S3: {str(e)}")
