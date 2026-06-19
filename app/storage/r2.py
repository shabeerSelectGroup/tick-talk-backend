"""Cloudflare R2 (S3-compatible) storage backend."""

import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.storage.base import StorageBackend, StorageError, StoredObjectRef


class R2StorageBackend(StorageBackend):
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None
        if self._settings.r2_endpoint_url and self._settings.r2_access_key_id:
            self._client = boto3.client(
                "s3",
                endpoint_url=self._settings.r2_endpoint_url,
                aws_access_key_id=self._settings.r2_access_key_id,
                aws_secret_access_key=self._settings.r2_secret_access_key,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )

    def is_configured(self) -> bool:
        return self._client is not None

    def public_url(self, key: str) -> str:
        base = self._settings.r2_public_url.rstrip("/")
        if base:
            return f"{base}/{key}"
        return key

    def put_object(self, key: str, data: bytes, content_type: str) -> StoredObjectRef:
        if not self._client:
            raise StorageError("R2_NOT_CONFIGURED", "Cloudflare R2 is not configured.", 503)
        try:
            self._client.put_object(
                Bucket=self._settings.r2_bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
        except (ClientError, BotoCoreError) as e:
            raise StorageError(
                "R2_UPLOAD_FAILED",
                f"Failed to upload to R2: {e}",
                502,
            ) from e
        return StoredObjectRef(
            key=key,
            url=self.public_url(key),
            size_bytes=len(data),
            content_type=content_type,
        )

    def delete_object(self, key: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete_object(Bucket=self._settings.r2_bucket_name, Key=key)
        except (ClientError, BotoCoreError):
            pass

    def create_presigned_upload_url(self, key: str, expires_in: int = 3600) -> str:
        if not self._client:
            raise StorageError("R2_NOT_CONFIGURED", "Cloudflare R2 is not configured.", 503)
        try:
            return self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._settings.r2_bucket_name,
                    "Key": key,
                    "ContentType": "image/jpeg",
                },
                ExpiresIn=expires_in,
            )
        except (ClientError, BotoCoreError) as e:
            raise StorageError("R2_PRESIGN_FAILED", str(e), 502) from e

    @staticmethod
    def new_object_id() -> str:
        return uuid.uuid4().hex
