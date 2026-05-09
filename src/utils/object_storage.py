"""S3-compatible object storage client.

Per-user credentials are sourced from :mod:`src.runtime`. The same code
path serves MinIO (self-hosted) and Aliyun OSS (which exposes an S3
endpoint at ``oss-<region>.aliyuncs.com``). Other S3-compatible
backends (Cloudflare R2, Backblaze B2, AWS S3, …) work too — the user
only changes ``STORAGE_PROVIDER`` / ``STORAGE_ENDPOINT`` /
``STORAGE_REGION``.

Storage modes (per-user):

* ``minio``       — required: endpoint, access key, secret key, bucket
* ``aliyun_oss``  — same fields; endpoint is something like
                    ``https://oss-cn-beijing.aliyuncs.com``
* ``local_only``  — no remote storage; the client is a no-op so callers
                    can keep the same call sites
"""

from __future__ import annotations

import ipaddress
import logging
import os
import threading
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from src.runtime import current_user_id, get_cred


def _endpoint_is_internal(endpoint: str) -> bool:
    """Heuristic: is this endpoint host unreachable from the public net?

    True for:
      - empty/missing endpoint
      - hostnames without a dot (Docker compose service names like ``minio``)
      - ``localhost``
      - RFC1918 / loopback IPs (10/8, 172.16/12, 192.168/16, 127/8)
      - link-local (169.254/16)
    False for everything else (FQDNs like ``oss-cn-beijing.aliyuncs.com``).
    """
    if not endpoint:
        return True
    try:
        host = (urlparse(endpoint).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return True
    if host == "localhost" or "." not in host:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local

logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StorageConfig:
    provider: str  # "minio" | "aliyun_oss" | "local_only"
    endpoint: str
    region: str
    access_key: str
    secret_key: str
    bucket: str
    path_prefix: str

    @classmethod
    def from_runtime(cls) -> "StorageConfig":
        provider = (get_cred("STORAGE_PROVIDER") or "local_only").strip().lower()
        if provider not in ("minio", "aliyun_oss", "local_only"):
            logger.warning("Unknown STORAGE_PROVIDER=%s; treating as local_only", provider)
            provider = "local_only"

        # Pull legacy Aliyun OSS_* fields as fallbacks so users who haven't
        # migrated to STORAGE_* keys still see their data.
        endpoint = get_cred("STORAGE_ENDPOINT") or get_cred("OSS_ENDPOINT") or ""
        access_key = (
            get_cred("STORAGE_ACCESS_KEY")
            or get_cred("ALIBABA_CLOUD_ACCESS_KEY_ID")
            or ""
        )
        secret_key = (
            get_cred("STORAGE_SECRET_KEY")
            or get_cred("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
            or ""
        )
        bucket = get_cred("STORAGE_BUCKET") or get_cred("OSS_BUCKET_NAME") or ""
        prefix = (get_cred("STORAGE_PATH_PREFIX") or get_cred("OSS_BASE_PATH") or "manju-forge").strip("/")
        # Multi-tenant key scoping: anchor every object under
        # ``<prefix>/users/<uid>``. Without this, two users sharing one bucket
        # (the deploy-compose default — MinIO root creds + single bucket)
        # can read each other's data by guessing object keys, since the
        # presigned-URL endpoint signs anything in the bucket.
        uid = current_user_id()
        if uid is not None:
            prefix = f"{prefix}/users/{uid}"
        region = get_cred("STORAGE_REGION") or "us-east-1"

        # Normalise endpoint for Aliyun OSS: "oss-cn-beijing.aliyuncs.com" → full URL
        if endpoint and not endpoint.startswith(("http://", "https://")):
            endpoint = "https://" + endpoint

        return cls(
            provider=provider,
            endpoint=endpoint,
            region=region,
            access_key=access_key,
            secret_key=secret_key,
            bucket=bucket,
            path_prefix=prefix,
        )

    @property
    def is_remote(self) -> bool:
        return self.provider in ("minio", "aliyun_oss")

    @property
    def is_configured(self) -> bool:
        if not self.is_remote:
            return False
        return all([self.endpoint, self.access_key, self.secret_key, self.bucket])

    def signature(self) -> tuple:
        return (
            self.provider,
            self.endpoint,
            self.region,
            self.access_key,
            self.secret_key,
            self.bucket,
            self.path_prefix,
        )


# ── Client ────────────────────────────────────────────────────────────────


class ObjectStorageClient:
    """A thin per-user wrapper over :mod:`boto3` S3."""

    _instances: dict[tuple, "ObjectStorageClient"] = {}
    _lock = threading.RLock()

    def __init__(self, config: StorageConfig):
        self.config = config
        self._s3 = None  # lazy

        if config.is_configured:
            try:
                import boto3  # local import: optional dep at runtime
                from botocore.client import Config as BotoConfig

                self._s3 = boto3.client(
                    "s3",
                    endpoint_url=config.endpoint,
                    aws_access_key_id=config.access_key,
                    aws_secret_access_key=config.secret_key,
                    region_name=config.region,
                    config=BotoConfig(signature_version="s3v4", retries={"max_attempts": 3}),
                )
            except Exception as e:  # pragma: no cover
                logger.error("Failed to construct S3 client: %s", e)
                self._s3 = None

    # ── Class-level resolver ─────────────────────────────────────────────

    @classmethod
    def for_current_user(cls) -> "ObjectStorageClient":
        cfg = StorageConfig.from_runtime()
        sig = (current_user_id(), cfg.signature())
        with cls._lock:
            inst = cls._instances.get(sig)
            if inst is None:
                inst = cls(cfg)
                cls._instances[sig] = inst
            return inst

    @classmethod
    def reset_cache(cls, user_id: Optional[int] = None) -> None:
        with cls._lock:
            if user_id is None:
                cls._instances.clear()
                return
            stale = [k for k in cls._instances if k[0] == user_id]
            for k in stale:
                cls._instances.pop(k, None)

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def is_configured(self) -> bool:
        return self._s3 is not None and self.config.is_configured

    @property
    def bucket(self) -> str:
        return self.config.bucket

    # ── Operations ───────────────────────────────────────────────────────

    def _full_key(self, key: str) -> str:
        key = key.lstrip("/")
        prefix = self.config.path_prefix.strip("/")
        if prefix:
            return f"{prefix}/{key}"
        return key

    def upload_file(self, local_path: str, key: str) -> Optional[str]:
        """Upload ``local_path`` to ``<prefix>/<key>``. Returns the full
        object key on success or None on failure / when not configured."""
        if not self.is_configured:
            return None
        full_key = self._full_key(key)
        try:
            self._s3.upload_file(local_path, self.config.bucket, full_key)
            return full_key
        except Exception as e:
            logger.exception("upload_file failed: %s", e)
            return None

    def upload_bytes(self, data: bytes, key: str, content_type: Optional[str] = None) -> Optional[str]:
        if not self.is_configured:
            return None
        full_key = self._full_key(key)
        kwargs = {"Bucket": self.config.bucket, "Key": full_key, "Body": data}
        if content_type:
            kwargs["ContentType"] = content_type
        try:
            self._s3.put_object(**kwargs)
            return full_key
        except Exception as e:
            logger.exception("upload_bytes failed: %s", e)
            return None

    def delete_object(self, key: str) -> bool:
        if not self.is_configured:
            return False
        full_key = self._full_key(key) if not key.startswith(self.config.path_prefix) else key
        try:
            self._s3.delete_object(Bucket=self.config.bucket, Key=full_key)
            return True
        except Exception as e:
            logger.warning("delete_object failed: %s", e)
            return False

    def presigned_get_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        if not self.is_configured:
            return None
        full_key = key
        if not full_key.startswith(self.config.path_prefix):
            full_key = self._full_key(key)
        try:
            return self._s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.config.bucket, "Key": full_key},
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.warning("presigned_get_url failed: %s", e)
            return None

    def download_bytes(self, key: str) -> Optional[bytes]:
        """Fetch the raw bytes of ``key`` from the bucket.

        Used when a presigned URL would point at an internal-only endpoint
        (e.g. ``http://minio:9000``) that an external API like DashScope
        can't reach. Reading via the same boto3 client uses whichever
        endpoint the backend can reach (typically the Docker-internal one),
        so the bytes can then be inlined as base64.
        """
        if not self.is_configured:
            return None
        full_key = key
        if not full_key.startswith(self.config.path_prefix):
            full_key = self._full_key(key)
        try:
            resp = self._s3.get_object(Bucket=self.config.bucket, Key=full_key)
            return resp["Body"].read()
        except Exception as e:
            logger.warning("download_bytes failed for %s: %s", full_key, e)
            return None

    @property
    def endpoint_is_internal(self) -> bool:
        """True when the configured endpoint host is unreachable from the
        public internet (Docker hostname, localhost, RFC1918 IP, …).

        Used by callers that need a publicly reachable URL — like
        DashScope image inputs — to decide between handing out a presigned
        URL vs. downloading bytes and inlining as base64.
        """
        return _endpoint_is_internal(self.config.endpoint)

    def presigned_put_url(self, key: str, expires_in: int = 600) -> Optional[str]:
        if not self.is_configured:
            return None
        full_key = self._full_key(key)
        try:
            return self._s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": self.config.bucket, "Key": full_key},
                ExpiresIn=expires_in,
            )
        except Exception as e:
            logger.warning("presigned_put_url failed: %s", e)
            return None
