"""Unified object storage: local disk or Aliyun OSS."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse

import alibabacloud_oss_v2 as oss

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def public_url(self, key: str) -> str: ...


_storage_override: ObjectStorage | None = None


def is_oss_configured(settings: Settings | None = None) -> bool:
    """True when AccessKey pair, bucket, and endpoint or region are all set."""
    s = settings or get_settings()
    if not s.oss_access_key_id or not s.oss_access_key_secret or not s.oss_bucket:
        return False
    return bool(s.oss_endpoint or s.oss_region)


class LocalObjectStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        cleaned = key.replace("\\", "/").lstrip("/")
        path = (self.root / cleaned).resolve()
        root = self.root.resolve()
        if not str(path).startswith(str(root)):
            raise ValueError(f"invalid storage key: {key}")
        return path

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        return path.read_bytes()

    def delete(self, key: str) -> None:
        if not key:
            return
        path = self._path(key)
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            logger.warning("failed to delete local object key=%s path=%s", key, path)

    def public_url(self, key: str) -> str:
        cleaned = key.replace("\\", "/").lstrip("/")
        return f"/uploads/{cleaned}"


class OssObjectStorage:
    def __init__(
        self,
        *,
        bucket: str,
        access_key_id: str,
        access_key_secret: str,
        region: str = "",
        endpoint: str = "",
        client: oss.Client | None = None,
    ) -> None:
        self.bucket = bucket
        self.region = region.strip() or "cn-hangzhou"
        self.endpoint = endpoint.strip()
        if client is not None:
            self._client = client
        else:
            cfg = oss.config.load_default()
            cfg.credentials_provider = oss.credentials.StaticCredentialsProvider(
                access_key_id,
                access_key_secret,
            )
            cfg.region = self.region
            if self.endpoint:
                cfg.endpoint = self.endpoint
            self._client = oss.Client(cfg)

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        kwargs: dict = {"bucket": self.bucket, "key": key, "body": data}
        if content_type:
            kwargs["content_type"] = content_type
        self._client.put_object(oss.PutObjectRequest(**kwargs))

    def get(self, key: str) -> bytes:
        result = self._client.get_object(oss.GetObjectRequest(bucket=self.bucket, key=key))
        with result.body as body:
            return body.read()

    def delete(self, key: str) -> None:
        if not key:
            return
        try:
            self._client.delete_object(
                oss.DeleteObjectRequest(bucket=self.bucket, key=key)
            )
        except Exception:  # noqa: BLE001
            logger.warning("failed to delete OSS object key=%s", key, exc_info=True)

    def public_url(self, key: str) -> str:
        cleaned = key.replace("\\", "/").lstrip("/")
        host = self._public_host()
        return f"https://{host}/{cleaned}"

    def _public_host(self) -> str:
        """Virtual-hosted style: {bucket}.oss-cn-hangzhou.aliyuncs.com"""
        if self.endpoint:
            ep = self.endpoint.strip()
            if "://" in ep:
                ep = urlparse(ep).netloc or ep.split("://", 1)[1]
            ep = ep.rstrip("/")
            # endpoint like oss-cn-hangzhou.aliyuncs.com
            if ep.startswith(f"{self.bucket}."):
                return ep
            return f"{self.bucket}.{ep}"
        return f"{self.bucket}.oss-{self.region}.aliyuncs.com"


def get_object_storage(settings: Settings | None = None) -> ObjectStorage:
    if _storage_override is not None:
        return _storage_override
    s = settings or get_settings()
    if is_oss_configured(s):
        return OssObjectStorage(
            bucket=s.oss_bucket,
            access_key_id=s.oss_access_key_id,
            access_key_secret=s.oss_access_key_secret,
            region=s.oss_region,
            endpoint=s.oss_endpoint,
        )
    return LocalObjectStorage(s.upload_dir)


def override_object_storage(storage: ObjectStorage | None) -> None:
    """Test helper: inject a fake storage backend (None clears override)."""
    global _storage_override
    _storage_override = storage


_AVATAR_UPLOADS_RE = re.compile(r"^/uploads/(avatars/.+)$")


def avatar_key_from_url(url: str | None) -> str | None:
    """Extract object key from a stored avatar_url, if it belongs to this app."""
    if not url:
        return None
    url = url.strip()
    m = _AVATAR_UPLOADS_RE.match(url)
    if m:
        return m.group(1)
    if url.startswith("http://") or url.startswith("https://"):
        path = urlparse(url).path.lstrip("/")
        if path.startswith("avatars/"):
            return path
    if url.startswith("avatars/"):
        return url
    return None
