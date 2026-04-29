import os
import oss2
import hashlib
import time
import threading
from typing import Optional, Tuple
from . import get_logger
from .media_refs import classify_media_ref, MEDIA_REF_LOCAL_PATH, MEDIA_REF_OBJECT_KEY
from src.runtime import current_user_id, get_cred

logger = get_logger(__name__)

# Default configuration
DEFAULT_OSS_BASE_PATH = "manju-forge"
SIGN_URL_EXPIRES_DISPLAY = 7200  # 2 hours for frontend display
SIGN_URL_EXPIRES_API = 1800      # 30 minutes for AI API calls


def is_oss_configured() -> bool:
    """Check if OSS is properly configured for the current request's user
    (or the process environment outside a request)."""
    required = [
        get_cred("ALIBABA_CLOUD_ACCESS_KEY_ID"),
        get_cred("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
        get_cred("OSS_ENDPOINT"),
        get_cred("OSS_BUCKET_NAME"),
    ]
    return all(required)


def get_oss_base_path() -> str:
    """Get OSS base path from current credentials / env, falling back to default."""
    return (get_cred("OSS_BASE_PATH") or DEFAULT_OSS_BASE_PATH).rstrip("/")


def is_object_key(value: str) -> bool:
    """
    Check if a string value is an OSS Object Key (not a full URL or local path).
    """
    return (
        classify_media_ref(value, oss_base_path=get_oss_base_path())
        == MEDIA_REF_OBJECT_KEY
    )

def is_local_path(value: str) -> bool:
    """Check if a string is a local file path (relative or absolute)."""
    return (
        classify_media_ref(value, oss_base_path=get_oss_base_path())
        == MEDIA_REF_LOCAL_PATH
    )


class OSSImageUploader:
    """
    OSS Uploader supporting Private OSS + Dynamic Signing strategy.
    
    Key principles:
    - Upload files and return Object Keys (not full URLs)
    - Generate signed URLs on-demand with configurable expiry
    - Support both private bucket access and AI API access
    """
    
    # Per-user singleton: each authenticated user has their own OSS keys, so
    # we cache one OSSImageUploader per user_id (and a single None-keyed
    # instance for non-request contexts: the startup log, scripts, tests).
    _instances: dict = {}
    _instances_lock = threading.RLock()

    # Maximum number of (object_key, expires) pairs to remember per uploader
    # before we start evicting the least-recently-inserted entry. Keeps the
    # cache from growing unbounded across long-running processes.
    _URL_CACHE_MAX = 1024

    def __new__(cls):
        key = current_user_id()
        with cls._instances_lock:
            inst = cls._instances.get(key)
            if inst is None:
                inst = super().__new__(cls)
                inst._initialized = False
                # OrderedDict gives O(1) move-to-end for LRU touch.
                from collections import OrderedDict
                inst._url_cache = OrderedDict()
                cls._instances[key] = inst
            return inst

    def __init__(self):
        if self._initialized:
            return

        self.access_key_id = get_cred("ALIBABA_CLOUD_ACCESS_KEY_ID")
        self.access_key_secret = get_cred("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        self.endpoint = get_cred("OSS_ENDPOINT")
        self.bucket_name = get_cred("OSS_BUCKET_NAME")
        self.base_path = get_oss_base_path()

        # Prefer the S3-compatible backend when ``STORAGE_PROVIDER`` is
        # explicitly set (minio / aliyun_oss). The legacy oss2 path below
        # still runs as a fallback when the user has only the old
        # ``OSS_*`` keys configured.
        provider = (get_cred("STORAGE_PROVIDER") or "").strip().lower()
        if provider in ("minio", "aliyun_oss"):
            from .object_storage import ObjectStorageClient

            self._s3_backend = ObjectStorageClient.for_current_user()
            if self._s3_backend.is_configured:
                self.bucket = self._s3_backend  # truthy + carries the bucket
                self._initialized = True
                logger.info(
                    "OSS backend: %s (bucket=%s, prefix=%s)",
                    provider,
                    self._s3_backend.bucket,
                    self._s3_backend.config.path_prefix,
                )
                return
        else:
            self._s3_backend = None
        
        # Debug prints for terminal
        print(f"DEBUG: OSS init - ID={'***' if self.access_key_id else 'None'}, Secret={'***' if self.access_key_secret else 'None'}, Endpoint={self.endpoint}, Bucket={self.bucket_name}, Base={self.base_path}")
        
        if not all([self.access_key_id, self.access_key_secret, self.endpoint, self.bucket_name]):
            logger.warning("OSS credentials not fully configured. OSS upload will be disabled.")
            print("DEBUG: OSS init - FAILED: missing credentials")
            self.bucket = None
        else:
            try:
                self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)
                # Set connection timeout to prevent long blocking on network issues
                self.bucket = oss2.Bucket(
                    self.auth, 
                    self.endpoint, 
                    self.bucket_name,
                    connect_timeout=5  # 5 seconds connection timeout
                )
                logger.info(f"OSS initialized: bucket={self.bucket_name}, base_path={self.base_path}")
                print(f"DEBUG: OSS init - SUCCESS: bucket={self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize OSS bucket: {e}")
                print(f"DEBUG: OSS init - ERROR: {e}")
                self.bucket = None
        
        self._initialized = True

    
    @classmethod
    def reset_instance(cls, user_id: Optional[int] = None):
        """Reset cached uploader(s).

        Without args, drops *all* per-user instances (used after global
        config changes). With ``user_id`` set, drops only that user's
        cache so subsequent requests rebuild with the new credentials.
        """
        with cls._instances_lock:
            if user_id is None:
                cls._instances.clear()
            else:
                cls._instances.pop(user_id, None)
    
    @property
    def is_configured(self) -> bool:
        """Check if OSS is properly configured and ready."""
        return self.bucket is not None
    
    def _build_object_key(self, sub_path: str, filename: str) -> str:
        """
        Build full Object Key from base path, sub path, and filename.
        
        Example: manju-forge/proj_123/assets/characters/char_001.png
        """
        parts = [self.base_path]
        if sub_path:
            parts.append(sub_path.strip("/"))
        parts.append(filename)
        return "/".join(parts)
    
    def upload_file(self, local_path: str, sub_path: str = "", custom_filename: str = None) -> Optional[str]:
        """
        Upload a file to object storage and return the Object Key.

        Args:
            local_path: Local file path to upload
            sub_path: Sub-directory path (e.g., "proj_123/assets/characters")
            custom_filename: Optional custom filename, defaults to original filename

        Returns:
            Object Key (e.g., "manju-forge/proj_123/assets/characters/file.png") or None if failed
        """
        if not self.bucket:
            logger.warning("OSS not configured, cannot upload file.")
            return None

        if not os.path.exists(local_path):
            logger.error(f"File not found: {local_path}")
            return None

        filename = custom_filename or os.path.basename(local_path)

        # MinIO / S3-compatible backend
        if self._s3_backend is not None:
            rel_key = "/".join(p for p in [sub_path.strip("/"), filename] if p)
            return self._s3_backend.upload_file(local_path, rel_key)

        # Legacy oss2 path (Aliyun OSS via Aliyun SDK)
        try:
            object_key = self._build_object_key(sub_path, filename)
            logger.info(f"Uploading to OSS: {local_path} -> {object_key}")

            with open(local_path, 'rb') as f:
                result = self.bucket.put_object(object_key, f)

            if result.status == 200:
                logger.info(f"Upload success: {object_key}")
                return object_key
            logger.error(f"Upload failed with status: {result.status}")
            return None
        except Exception as e:
            logger.error(f"OSS upload error: {e}")
            return None
    
    def generate_signed_url(self, object_key: str, expires: int = SIGN_URL_EXPIRES_DISPLAY) -> str:
        """Generate a signed GET URL valid for ``expires`` seconds."""
        if not self.bucket:
            logger.warning("OSS not configured, cannot generate signed URL.")
            return ""

        # Cache: reuse a signed URL while at least 10 minutes of validity remain.
        cache_key = (object_key, expires)
        now = time.time()
        if cache_key in self._url_cache:
            cached_url, timestamp = self._url_cache[cache_key]
            if now - timestamp < (expires - 600):
                self._url_cache.move_to_end(cache_key)  # LRU touch
                return cached_url

        def _remember(url_value: str) -> None:
            self._url_cache[cache_key] = (url_value, now)
            self._url_cache.move_to_end(cache_key)
            while len(self._url_cache) > self._URL_CACHE_MAX:
                self._url_cache.popitem(last=False)

        # MinIO / S3-compatible backend
        if self._s3_backend is not None:
            url = self._s3_backend.presigned_get_url(object_key, expires_in=expires) or ""
            if url:
                _remember(url)
            return url

        # Legacy oss2 path
        try:
            url = self.bucket.sign_url('GET', object_key, expires, slash_safe=True)
            if url.startswith("http://"):
                url = "https://" + url[7:]
            _remember(url)
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {object_key}: {e}")
            return ""
    
    def sign_url_for_display(self, object_key: str) -> str:
        """Generate signed URL for frontend display (2 hours validity)."""
        signed_url = self.generate_signed_url(object_key, SIGN_URL_EXPIRES_DISPLAY)
        # print(f"DEBUG: sign_url_for_display('{object_key}') -> '{signed_url}'")
        return signed_url


    
    def sign_url_for_api(self, object_key: str) -> str:
        """Generate signed URL for AI API calls (30 minutes validity)."""
        return self.generate_signed_url(object_key, SIGN_URL_EXPIRES_API)
    
    def object_exists(self, object_key: str) -> bool:
        """Check if an object exists in OSS."""
        if not self.bucket:
            return False
        if self._s3_backend is not None:
            try:
                self._s3_backend._s3.head_object(Bucket=self._s3_backend.bucket, Key=object_key)
                return True
            except Exception:
                return False
        try:
            return self.bucket.object_exists(object_key)
        except Exception:
            return False
    
    # Legacy methods for backward compatibility
    def upload_image(self, local_image_path: str, sub_path: str = "assets") -> Optional[str]:
        """Legacy method: Upload image and return Object Key."""
        return self.upload_file(local_image_path, sub_path)
    
    def upload_video(self, local_video_path: str, sub_path: str = "video") -> Optional[str]:
        """Legacy method: Upload video and return Object Key."""
        return self.upload_file(local_video_path, sub_path)
    
    def get_oss_url(self, object_key: str, use_public_url: bool = False) -> str:
        """
        Legacy method: Get OSS URL.
        
        Note: For Private OSS strategy, always use signed URLs.
        The use_public_url parameter is deprecated.
        """
        if use_public_url:
            logger.warning("Public URLs are deprecated. Using signed URL instead for security.")
        return self.sign_url_for_display(object_key)


def sign_oss_urls_in_data(data, uploader: OSSImageUploader = None):
    """
    Recursively traverse data structure and convert Object Keys to signed URLs.
    
    This is the core function for the "Dynamic Signing" strategy.
    Called before returning API responses to frontend.
    
    Args:
        data: Dict, list, or primitive value to process
        uploader: OSSImageUploader instance (created if not provided)
    
    Returns:
        Processed data with Object Keys converted to signed URLs
    """
    if uploader is None:
        uploader = OSSImageUploader()
    
    if not uploader.is_configured:
        # OSS not configured, return data as-is (local mode)
        return data
    
    def process_value(value):
        if isinstance(value, str):
            if is_object_key(value):
                signed_url = uploader.sign_url_for_display(value)
                return signed_url if signed_url else value
            # print(f"DEBUG: sign_oss_urls_in_data - skipping string '{value[:50]}...'")
            return value
        elif isinstance(value, dict):
            return {k: process_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [process_value(item) for item in value]
        else:
            return value
    
    return process_value(data)


def convert_local_path_to_object_key(local_path: str, project_id: str = None) -> str:
    """
    Convert a local relative path to an OSS Object Key format.
    
    Example: 
        "assets/characters/char_001.png" -> "manju-forge/proj_123/assets/characters/char_001.png"
    """
    base_path = get_oss_base_path()
    
    # Remove "output/" prefix if present
    if local_path.startswith("output/"):
        local_path = local_path[7:]
    
    # Build Object Key
    if project_id:
        return f"{base_path}/{project_id}/{local_path}"
    else:
        return f"{base_path}/{local_path}"
