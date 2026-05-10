import base64
import logging
import mimetypes
import os
import tempfile
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Callable, Dict, List, Mapping, Optional, Sequence

import requests

from .media_refs import (
    MEDIA_REF_BLOB_URL,
    MEDIA_REF_DATA_URI,
    MEDIA_REF_LOCAL_PATH,
    MEDIA_REF_OBJECT_KEY,
    MEDIA_REF_REMOTE_URL,
    classify_media_ref,
    resolve_local_media_path,
)
from .provider_registry import (
    SUPPORTED_PROVIDER_BACKENDS,
    ProviderRegistry,
    get_default_provider_registry,
)

logger = logging.getLogger(__name__)


RESOLVE_HEADER_DASHSCOPE_OSS_RESOURCE = "X-DashScope-OssResourceResolve"
_DASHSCOPE_TEMP_SUB_PATH = "temp/provider_media"


@dataclass(frozen=True)
class ResolvedMediaInput:
    value: str
    headers: Mapping[str, str] = field(default_factory=dict)
    source_ref: Optional[str] = None
    media_ref_type: Optional[str] = None

    def __post_init__(self):
        immutable_headers = MappingProxyType(dict(self.headers or {}))
        object.__setattr__(self, "headers", immutable_headers)


def _normalize_modality(modality: str) -> str:
    value = (modality or "").strip().lower()
    if value in {"image", "audio", "video", "reference_video"}:
        return value
    raise ValueError(f"Unsupported modality '{modality}'")


def _mode_for_modality(family_config, backend: str, modality: str) -> str:
    if modality == "image":
        mode = family_config.image_input_mode.get(backend)
    elif modality == "audio":
        mode = family_config.audio_input_mode.get(backend)
    else:
        mode = family_config.reference_video_input_mode.get(backend)

    if mode:
        return mode
    raise ValueError(
        f"Model family '{family_config.model_family}' does not support backend "
        f"'{backend}' for modality '{modality}'"
    )


def _encode_image_as_data_uri(local_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(local_path)
    if not mime_type:
        mime_type = "image/png"
    with open(local_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _encode_local_file_base64(local_path: str) -> str:
    with open(local_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _strip_data_uri_prefix(value: str) -> str:
    if ";base64," in value and value.startswith("data:"):
        return value.split(";base64,", 1)[1]
    return value


def _signed_url_from_object_key(ref: str, uploader) -> Optional[str]:
    if not uploader or not getattr(uploader, "is_configured", False):
        return None
    return uploader.sign_url_for_api(ref)


def _upload_then_sign(local_path: str, uploader, sub_path: str = _DASHSCOPE_TEMP_SUB_PATH) -> Optional[str]:
    if not uploader or not getattr(uploader, "is_configured", False):
        return None
    object_key = uploader.upload_file(local_path, sub_path=sub_path)
    if not object_key:
        return None
    return uploader.sign_url_for_api(object_key)


def _resolved(value: str, *, source_ref: str, media_ref_type: str, headers: Optional[Dict[str, str]] = None) -> ResolvedMediaInput:
    return ResolvedMediaInput(
        value=value,
        headers=headers or {},
        source_ref=source_ref,
        media_ref_type=media_ref_type,
    )


def _resolve_dashscope_image(
    ref: str,
    ref_type: str,
    *,
    uploader,
    local_path: Optional[str],
) -> ResolvedMediaInput:
    inlined = _try_inline_for_internal_endpoint(
        ref, ref_type, uploader=uploader, local_path=local_path
    )
    if inlined is not None:
        return inlined

    if ref_type in (MEDIA_REF_REMOTE_URL, MEDIA_REF_DATA_URI):
        return _resolved(ref, source_ref=ref, media_ref_type=ref_type)
    if ref_type == MEDIA_REF_OBJECT_KEY:
        signed_url = _signed_url_from_object_key(ref, uploader)
        if signed_url:
            return _resolved(signed_url, source_ref=ref, media_ref_type=ref_type)
        raise ValueError(
            "DashScope image input received an OSS object key but OSS is not configured. "
            "Configure OSS or pass a local/remote image reference."
        )
    if ref_type == MEDIA_REF_LOCAL_PATH:
        if not local_path:
            raise ValueError(f"Unable to resolve local media path for '{ref}'")
        signed_url = _upload_then_sign(local_path, uploader)
        if signed_url:
            return _resolved(signed_url, source_ref=ref, media_ref_type=ref_type)
        return _resolved(_encode_image_as_data_uri(local_path), source_ref=ref, media_ref_type=ref_type)
    if ref_type == MEDIA_REF_BLOB_URL:
        raise ValueError("Blob URLs are ephemeral and unsupported for backend media resolution.")
    raise ValueError(f"Unsupported media reference for DashScope image input: '{ref}'")


def _download_object_as_data_uri(object_key: str, uploader) -> Optional[str]:
    """Fetch bytes for ``object_key`` via the uploader and wrap as a data URI."""
    download_bytes = getattr(uploader, "download_bytes", None)
    if not callable(download_bytes):
        return None
    try:
        raw = download_bytes(object_key)
    except Exception:
        return None
    if not raw:
        return None
    mime_type, _ = mimetypes.guess_type(object_key)
    if not mime_type:
        mime_type = "image/png"
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _try_inline_for_internal_endpoint(
    ref: str,
    ref_type: str,
    *,
    uploader,
    local_path: Optional[str],
) -> Optional[ResolvedMediaInput]:
    """Inline bytes as base64 when the storage endpoint is internal-only.

    Self-hosted MinIO behind a Docker hostname like ``http://minio:9000``
    is unreachable from DashScope, so any presigned URL we'd hand out
    would fail with ``InvalidParameter.DataInspection: Unable to download
    the media resource``. The backend can still reach the bytes itself,
    so wrap them as a data URI — DashScope accepts that natively in
    ``input.media`` / image-message content.

    Returns ``None`` when inlining isn't applicable (public endpoint,
    no uploader, unsupported ref type, or fetch failure) so the caller
    falls through to its normal signed-URL path.

    A pre-existing data URI just passes through, since the bytes are
    already self-contained.
    """
    if not (uploader and getattr(uploader, "prefers_inline_for_api", False)):
        return None

    if ref_type == MEDIA_REF_DATA_URI:
        return _resolved(ref, source_ref=ref, media_ref_type=ref_type)

    data_uri: Optional[str] = None
    if ref_type == MEDIA_REF_REMOTE_URL:
        data_uri = _fetch_url_as_data_uri(ref)
        if not data_uri:
            logger.warning(
                "Internal-endpoint inline fetch failed for %s; falling through. "
                "DashScope may reject if the host is unreachable.",
                ref,
            )
    elif ref_type == MEDIA_REF_OBJECT_KEY:
        data_uri = _download_object_as_data_uri(ref, uploader)
    elif ref_type == MEDIA_REF_LOCAL_PATH and local_path:
        data_uri = _encode_image_as_data_uri(local_path)

    if data_uri:
        return _resolved(data_uri, source_ref=ref, media_ref_type=ref_type)
    return None


def _fetch_url_as_data_uri(url: str, *, timeout: int = 60) -> Optional[str]:
    """GET ``url`` and wrap the response body as a base64 data URI.

    Used when ``prefer_inline_for_api`` is True and the ref is already a
    full URL (typically a presigned URL pointing at an internal-only
    storage endpoint that DashScope cannot reach). The backend container
    can reach the URL itself, so fetching + inlining keeps the call
    working without leaking the internal hostname.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger.debug("Failed to fetch URL for inlining: %s — %s", url, e)
        return None
    if not resp.content:
        return None
    content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    if not content_type:
        # Strip query string before guessing from the path.
        path = url.split("?", 1)[0]
        content_type = mimetypes.guess_type(path)[0] or "image/png"
    encoded = base64.b64encode(resp.content).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _resolve_dashscope_temp_url(
    ref: str,
    ref_type: str,
    *,
    uploader,
    local_path: Optional[str],
    dashscope_temp_url_resolver: Optional[Callable[[str], str]],
) -> ResolvedMediaInput:
    inlined = _try_inline_for_internal_endpoint(
        ref, ref_type, uploader=uploader, local_path=local_path
    )
    if inlined is not None:
        return inlined

    if ref_type == MEDIA_REF_REMOTE_URL:
        return _resolved(ref, source_ref=ref, media_ref_type=ref_type)
    if ref_type == MEDIA_REF_OBJECT_KEY:
        signed_url = _signed_url_from_object_key(ref, uploader)
        if signed_url:
            return _resolved(signed_url, source_ref=ref, media_ref_type=ref_type)
        raise ValueError(
            "DashScope URL-based media input received an OSS object key but OSS is not configured. "
            "Configure OSS or use a local path that can be resolved via temporary URL."
        )
    if ref_type == MEDIA_REF_LOCAL_PATH:
        if not local_path:
            raise ValueError(f"Unable to resolve local media path for '{ref}'")
        signed_url = _upload_then_sign(local_path, uploader)
        if signed_url:
            return _resolved(signed_url, source_ref=ref, media_ref_type=ref_type)

        if dashscope_temp_url_resolver is None:
            raise ValueError(
                "DashScope URL-based media input requires OSS or a dashscope_temp_url_resolver "
                "for local media. Configure OSS or provide a DashScope temp-url resolver."
            )
        temp_url = dashscope_temp_url_resolver(local_path)
        if not isinstance(temp_url, str) or not temp_url.strip():
            raise ValueError("dashscope_temp_url_resolver returned an empty URL.")
        headers = {}
        if temp_url.startswith("oss://"):
            headers[RESOLVE_HEADER_DASHSCOPE_OSS_RESOURCE] = "enable"
        return _resolved(temp_url, source_ref=ref, media_ref_type=ref_type, headers=headers)
    if ref_type == MEDIA_REF_BLOB_URL:
        raise ValueError("Blob URLs are ephemeral and unsupported for backend media resolution.")
    raise ValueError(f"Unsupported media reference for DashScope URL-based media input: '{ref}'")


def _resolve_vendor_kling_image(
    ref: str,
    ref_type: str,
    *,
    local_path: Optional[str],
) -> ResolvedMediaInput:
    if ref_type == MEDIA_REF_LOCAL_PATH:
        if not local_path:
            raise ValueError(f"Unable to resolve local media path for '{ref}'")
        return _resolved(_encode_local_file_base64(local_path), source_ref=ref, media_ref_type=ref_type)
    if ref_type == MEDIA_REF_DATA_URI:
        return _resolved(_strip_data_uri_prefix(ref), source_ref=ref, media_ref_type=ref_type)
    raise ValueError(
        "Kling vendor image input requires local file or data URI so it can be sent as base64."
    )


def _resolve_vendor_url_mode(
    ref: str,
    ref_type: str,
    *,
    uploader,
    local_path: Optional[str],
    provider_label: str,
    modality: str,
) -> ResolvedMediaInput:
    if ref_type == MEDIA_REF_REMOTE_URL:
        return _resolved(ref, source_ref=ref, media_ref_type=ref_type)
    if ref_type == MEDIA_REF_OBJECT_KEY:
        signed_url = _signed_url_from_object_key(ref, uploader)
        if signed_url:
            return _resolved(signed_url, source_ref=ref, media_ref_type=ref_type)
    if ref_type == MEDIA_REF_LOCAL_PATH and local_path:
        signed_url = _upload_then_sign(local_path, uploader)
        if signed_url:
            return _resolved(signed_url, source_ref=ref, media_ref_type=ref_type)

    raise ValueError(
        f"{provider_label} vendor {modality} input requires a URL-compatible media source. "
        "Configure OSS for local/object-key references, or switch provider mode to dashscope."
    )


def resolve_media_input(
    ref: str,
    *,
    model_name: str,
    modality: str,
    backend: Optional[str] = None,
    uploader=None,
    registry: Optional[ProviderRegistry] = None,
    project_root: Optional[str] = None,
    oss_base_path: Optional[str] = None,
    dashscope_temp_url_resolver: Optional[Callable[[str], str]] = None,
) -> ResolvedMediaInput:
    """
    Resolve a stable project-side media reference to a provider-ready input payload.
    This function is pure with respect to caller state: it does not mutate `ref`.
    """
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("ref must be a non-empty string")

    active_registry = registry or get_default_provider_registry()
    family = active_registry.get_family_config(model_name)
    resolved_backend = (backend or active_registry.resolve_backend(model_name)).strip().lower()
    if resolved_backend not in SUPPORTED_PROVIDER_BACKENDS:
        raise ValueError(f"Unsupported backend '{resolved_backend}'")

    normalized_modality = _normalize_modality(modality)
    mode = _mode_for_modality(family, resolved_backend, normalized_modality)

    ref_type = classify_media_ref(
        ref,
        project_root=project_root,
        oss_base_path=oss_base_path,
    )
    local_path = resolve_local_media_path(ref, project_root=project_root)

    if mode in {"dashscope_multimodal_message", "dashscope_image_to_video"}:
        return _resolve_dashscope_image(
            ref,
            ref_type,
            uploader=uploader,
            local_path=local_path,
        )
    if mode == "dashscope_temp_file_url":
        return _resolve_dashscope_temp_url(
            ref,
            ref_type,
            uploader=uploader,
            local_path=local_path,
            dashscope_temp_url_resolver=dashscope_temp_url_resolver,
        )
    if mode == "kling_vendor_base64_image":
        return _resolve_vendor_kling_image(ref, ref_type, local_path=local_path)
    if (
        mode.startswith("vidu_vendor_")
        or mode.startswith("kling_vendor_")
        or mode.startswith("pixverse_vendor_")
    ):
        if mode.startswith("vidu_vendor_"):
            provider_label = "Vidu"
        elif mode.startswith("kling_vendor_"):
            provider_label = "Kling"
        else:
            provider_label = "Pixverse"
        return _resolve_vendor_url_mode(
            ref,
            ref_type,
            uploader=uploader,
            local_path=local_path,
            provider_label=provider_label,
            modality=normalized_modality,
        )

    raise ValueError(
        f"Unsupported provider media input mode '{mode}' for model '{model_name}' "
        f"(backend={resolved_backend}, modality={normalized_modality})."
    )


def resolve_media_inputs(
    refs: Sequence[str],
    *,
    model_name: str,
    modality: str,
    backend: Optional[str] = None,
    uploader=None,
    registry: Optional[ProviderRegistry] = None,
    project_root: Optional[str] = None,
    oss_base_path: Optional[str] = None,
    dashscope_temp_url_resolver: Optional[Callable[[str], str]] = None,
) -> List[ResolvedMediaInput]:
    return [
        resolve_media_input(
            ref,
            model_name=model_name,
            modality=modality,
            backend=backend,
            uploader=uploader,
            registry=registry,
            project_root=project_root,
            oss_base_path=oss_base_path,
            dashscope_temp_url_resolver=dashscope_temp_url_resolver,
        )
        for ref in list(refs)
    ]


def _write_temp_file(data: bytes, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


def _download_to_temp_file(url: str, suffix: str, *, timeout: int = 120) -> str:
    response = requests.get(url, stream=True, timeout=timeout)
    response.raise_for_status()
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return path


class MediaResolver:
    """Facade that turns any media reference into the form a caller wants.

    Use this when a provider adapter just needs a ready-to-send representation
    of a media reference and does NOT need the registry-driven backend ×
    modality dispatch performed by :func:`resolve_media_input`. The two are
    complementary:

    * :func:`resolve_media_input` — registered model families (Wan / Kling /
      Vidu / Pixverse). Picks DashScope multimodal vs vendor base64 vs vendor
      URL based on ``ProviderFamilyConfig``.
    * :class:`MediaResolver` — vendor adapters that already know what shape
      they want (Seedream, FLUX.2, Gemini Image, fal, Seedance, Hailuo,
      Veo, …). Just hand back a URL or a data URI / a local file.

    Every method accepts the four ref shapes used across the project:
    full http(s) URL, ``data:`` URI, output-relative local path, OSS
    object key.
    """

    def __init__(self, uploader=None, *, project_root: Optional[str] = None):
        self._uploader = uploader
        self._project_root = project_root

    @property
    def uploader(self):
        if self._uploader is None:
            from .oss_utils import OSSImageUploader
            self._uploader = OSSImageUploader()
        return self._uploader

    def _classify(self, ref: str) -> str:
        oss_base = None
        try:
            cfg = getattr(self.uploader, "base_path", None)
            if cfg:
                oss_base = cfg
        except Exception:
            oss_base = None
        return classify_media_ref(
            ref, oss_base_path=oss_base, project_root=self._project_root
        )

    def _resolve_local(self, ref: str) -> Optional[str]:
        return resolve_local_media_path(ref, project_root=self._project_root)

    def _prefers_inline(self) -> bool:
        try:
            return bool(getattr(self.uploader, "prefers_inline_for_api", False))
        except Exception:
            return False

    @staticmethod
    def _validate(ref: str) -> str:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError("media ref must be a non-empty string")
        return ref

    def to_url_or_inline(self, ref: str) -> str:
        """Return a URL the public internet can fetch, or a data URI when
        we can't hand one out (internal-only storage). Best fit for vendor
        APIs that accept either form on the same field.
        """
        self._validate(ref)
        rt = self._classify(ref)
        prefer_inline = self._prefers_inline()

        if rt == MEDIA_REF_DATA_URI:
            return ref

        if rt == MEDIA_REF_REMOTE_URL:
            if prefer_inline:
                inlined = _fetch_url_as_data_uri(ref)
                if inlined:
                    return inlined
            return ref

        if rt == MEDIA_REF_OBJECT_KEY:
            if not prefer_inline:
                signed = _signed_url_from_object_key(ref, self.uploader)
                if signed:
                    return signed
            inlined = _download_object_as_data_uri(ref, self.uploader)
            if inlined:
                return inlined
            raise RuntimeError(
                f"Cannot resolve OSS object key '{ref}': storage backend unavailable"
            )

        if rt == MEDIA_REF_LOCAL_PATH:
            local = self._resolve_local(ref)
            if not local or not os.path.exists(local):
                raise FileNotFoundError(f"Local media not found: {ref}")
            return _encode_image_as_data_uri(local)

        if rt == MEDIA_REF_BLOB_URL:
            raise ValueError(
                "Blob URLs are ephemeral and unsupported for backend media resolution"
            )

        # Last-ditch: an absolute path that classify didn't recognize as
        # output-relative (e.g. tests or callers passing temp files).
        if os.path.isabs(ref) and os.path.exists(ref):
            return _encode_image_as_data_uri(ref)
        raise ValueError(f"Unrecognized media reference: {ref}")

    def to_local_file(self, ref: str, *, suffix: str = ".bin") -> str:
        """Materialize as an on-disk file. Returns the existing path when ref
        is already a local file under ``output/``; otherwise writes a temp
        file the caller is responsible for cleaning up. Use this for
        ffmpeg / PIL / any API that expects a real file.
        """
        self._validate(ref)
        rt = self._classify(ref)

        if rt == MEDIA_REF_LOCAL_PATH:
            local = self._resolve_local(ref)
            if not local or not os.path.exists(local):
                raise FileNotFoundError(f"Local media not found: {ref}")
            return local

        if rt == MEDIA_REF_OBJECT_KEY:
            if not getattr(self.uploader, "is_configured", False):
                raise RuntimeError(
                    f"Cannot fetch OSS object '{ref}': storage backend not configured"
                )
            data = self.uploader.download_bytes(ref)
            if not data:
                raise RuntimeError(f"OSS object not found or empty: {ref}")
            return _write_temp_file(data, suffix)

        if rt == MEDIA_REF_REMOTE_URL:
            return _download_to_temp_file(ref, suffix)

        if rt == MEDIA_REF_DATA_URI:
            payload = _strip_data_uri_prefix(ref)
            return _write_temp_file(base64.b64decode(payload), suffix)

        if os.path.isabs(ref) and os.path.exists(ref):
            return ref

        raise ValueError(f"Unrecognized media reference: {ref}")

    def to_data_uri(self, ref: str) -> str:
        """Always inline as a ``data:`` URI. Use when the protocol does not
        accept URL forms (e.g. some OpenAI-compatible chat-completion
        ``image_url`` payloads must be self-contained)."""
        self._validate(ref)
        rt = self._classify(ref)

        if rt == MEDIA_REF_DATA_URI:
            return ref

        if rt == MEDIA_REF_REMOTE_URL:
            inlined = _fetch_url_as_data_uri(ref)
            if not inlined:
                raise RuntimeError(f"Failed to fetch URL for inlining: {ref}")
            return inlined

        if rt == MEDIA_REF_OBJECT_KEY:
            inlined = _download_object_as_data_uri(ref, self.uploader)
            if not inlined:
                raise RuntimeError(
                    f"Failed to inline OSS object (not configured or unreachable): {ref}"
                )
            return inlined

        if rt == MEDIA_REF_LOCAL_PATH:
            local = self._resolve_local(ref)
            if not local or not os.path.exists(local):
                raise FileNotFoundError(f"Local media not found: {ref}")
            return _encode_image_as_data_uri(local)

        if os.path.isabs(ref) and os.path.exists(ref):
            return _encode_image_as_data_uri(ref)
        raise ValueError(f"Unrecognized media reference: {ref}")

    def to_bytes(self, ref: str) -> bytes:
        """Raw bytes. Used for protocols that need explicit base64 encoding
        with their own field structure (e.g. Veo's ``inlineData``)."""
        data, _mime = self._fetch_bytes_and_mime(ref)
        return data

    def to_inline_blob(self, ref: str, *, default_mime: str = "image/png") -> "tuple[str, str]":
        """Return ``(mime_type, base64_data)`` for protocols that take raw
        inline blobs split across two fields (e.g. Gemini Image's
        ``inline_data``, Veo's ``image.bytesBase64Encoded``)."""
        data, mime = self._fetch_bytes_and_mime(ref)
        return mime or default_mime, base64.b64encode(data).decode("ascii")

    def _fetch_bytes_and_mime(self, ref: str) -> "tuple[bytes, Optional[str]]":
        self._validate(ref)
        rt = self._classify(ref)

        if rt == MEDIA_REF_DATA_URI:
            mime = None
            if ref.startswith("data:") and ";base64," in ref:
                mime = ref[len("data:"):].split(";", 1)[0] or None
            return base64.b64decode(_strip_data_uri_prefix(ref)), mime

        if rt == MEDIA_REF_REMOTE_URL:
            response = requests.get(ref, timeout=60)
            response.raise_for_status()
            mime = (response.headers.get("Content-Type") or "").split(";")[0].strip() or None
            return response.content, mime

        if rt == MEDIA_REF_OBJECT_KEY:
            if not getattr(self.uploader, "is_configured", False):
                raise RuntimeError(
                    f"Cannot fetch OSS object '{ref}': storage backend not configured"
                )
            data = self.uploader.download_bytes(ref)
            if not data:
                raise RuntimeError(f"OSS object not found or empty: {ref}")
            mime, _ = mimetypes.guess_type(ref)
            return data, mime

        if rt == MEDIA_REF_LOCAL_PATH:
            local = self._resolve_local(ref)
            if not local or not os.path.exists(local):
                raise FileNotFoundError(f"Local media not found: {ref}")
            mime, _ = mimetypes.guess_type(local)
            with open(local, "rb") as f:
                return f.read(), mime

        if os.path.isabs(ref) and os.path.exists(ref):
            mime, _ = mimetypes.guess_type(ref)
            with open(ref, "rb") as f:
                return f.read(), mime
        raise ValueError(f"Unrecognized media reference: {ref}")
