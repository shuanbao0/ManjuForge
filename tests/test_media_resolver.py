"""Unit tests for ``MediaResolver`` — the caller-driven media-input facade
introduced alongside the registry-driven :func:`resolve_media_input`.

Covers the four ref shapes (http URL / data URI / output-relative local
path / OSS object key) against the three primary methods
(``to_url_or_inline``, ``to_local_file``, ``to_inline_blob``), plus the
internal-endpoint path that drove the original bug — DashScope receiving
a bare ``manju-forge/...`` object key under self-hosted MinIO.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Optional

import pytest

from src.utils.provider_media import MediaResolver


PNG_1X1_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4//8/AwAI/AL+"
    "X2VINQAAAABJRU5ErkJggg=="
)
PNG_1X1_BYTES = base64.b64decode(PNG_1X1_BASE64)


class FakeUploader:
    def __init__(
        self,
        *,
        configured: bool = True,
        prefers_inline_for_api: bool = False,
        download_payload: Optional[dict] = None,
        base_path: str = "manju-forge",
    ):
        self.is_configured = configured
        self.prefers_inline_for_api = prefers_inline_for_api
        self.base_path = base_path
        self._download_payload = download_payload or {}
        self.signed_calls: list = []

    def sign_url_for_api(self, object_key: str) -> str:
        self.signed_calls.append(object_key)
        return f"https://oss.example/{object_key}"

    def download_bytes(self, object_key: str):
        return self._download_payload.get(object_key)


def _write_output_png(project_root: Path, rel_path: str) -> Path:
    file_path = project_root / "output" / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(PNG_1X1_BYTES)
    return file_path


# === to_url_or_inline ====================================================


def test_url_or_inline_passes_remote_url_through():
    uploader = FakeUploader(configured=False)
    resolver = MediaResolver(uploader)
    out = resolver.to_url_or_inline("https://example.com/image.png")
    assert out == "https://example.com/image.png"


def test_url_or_inline_passes_data_uri_through():
    uploader = FakeUploader(configured=False)
    resolver = MediaResolver(uploader)
    data_uri = f"data:image/png;base64,{PNG_1X1_BASE64}"
    assert resolver.to_url_or_inline(data_uri) == data_uri


def test_url_or_inline_local_path_returns_data_uri(tmp_path):
    _write_output_png(tmp_path, "uploads/ref.png")
    uploader = FakeUploader(configured=False)
    resolver = MediaResolver(uploader, project_root=str(tmp_path))
    out = resolver.to_url_or_inline("uploads/ref.png")
    assert out.startswith("data:image/png;base64,")


def test_url_or_inline_object_key_signs_when_endpoint_is_public():
    uploader = FakeUploader(configured=True, prefers_inline_for_api=False)
    resolver = MediaResolver(uploader)
    out = resolver.to_url_or_inline("manju-forge/users/1/storyboard/a.png")
    assert out == "https://oss.example/manju-forge/users/1/storyboard/a.png"
    assert uploader.signed_calls == ["manju-forge/users/1/storyboard/a.png"]


def test_url_or_inline_object_key_inlines_when_endpoint_is_internal():
    """Original bug scenario: MinIO behind ``http://minio:9000`` —
    presigned URLs are unreachable from external services, so the resolver
    must inline bytes via ``download_bytes``."""
    key = "manju-forge/users/1/storyboard/a.png"
    uploader = FakeUploader(
        configured=True,
        prefers_inline_for_api=True,
        download_payload={key: PNG_1X1_BYTES},
    )
    resolver = MediaResolver(uploader)
    out = resolver.to_url_or_inline(key)
    assert out.startswith("data:image/png;base64,")
    assert base64.b64decode(out.split(";base64,", 1)[1]) == PNG_1X1_BYTES
    assert uploader.signed_calls == []  # didn't fall back to a presigned URL


def test_url_or_inline_object_key_raises_when_uploader_not_configured():
    uploader = FakeUploader(configured=False)
    resolver = MediaResolver(uploader)
    with pytest.raises(RuntimeError, match="storage backend unavailable"):
        resolver.to_url_or_inline("manju-forge/users/1/x.png")


def test_url_or_inline_rejects_blob_url():
    resolver = MediaResolver(FakeUploader())
    with pytest.raises(ValueError, match="Blob URLs"):
        resolver.to_url_or_inline("blob:https://example.com/abc")


def test_url_or_inline_rejects_empty_ref():
    resolver = MediaResolver(FakeUploader())
    with pytest.raises(ValueError):
        resolver.to_url_or_inline("")


# === to_local_file =======================================================


def test_to_local_file_returns_existing_local_path(tmp_path):
    expected = _write_output_png(tmp_path, "uploads/ref.png")
    uploader = FakeUploader(configured=False)
    resolver = MediaResolver(uploader, project_root=str(tmp_path))
    out = resolver.to_local_file("uploads/ref.png", suffix=".png")
    assert Path(out).resolve() == expected.resolve()


def test_to_local_file_object_key_writes_temp(tmp_path):
    key = "manju-forge/users/1/video/a.mp4"
    uploader = FakeUploader(
        configured=True, download_payload={key: b"FAKE_MP4_BYTES"}
    )
    resolver = MediaResolver(uploader, project_root=str(tmp_path))
    out = resolver.to_local_file(key, suffix=".mp4")
    try:
        assert os.path.exists(out)
        assert out.endswith(".mp4")
        assert Path(out).read_bytes() == b"FAKE_MP4_BYTES"
    finally:
        os.remove(out)


def test_to_local_file_object_key_raises_when_uploader_unavailable():
    uploader = FakeUploader(configured=False)
    resolver = MediaResolver(uploader)
    with pytest.raises(RuntimeError, match="not configured"):
        resolver.to_local_file("manju-forge/users/1/video/a.mp4")


def test_to_local_file_data_uri_writes_temp():
    resolver = MediaResolver(FakeUploader())
    data_uri = f"data:image/png;base64,{PNG_1X1_BASE64}"
    out = resolver.to_local_file(data_uri, suffix=".png")
    try:
        assert Path(out).read_bytes() == PNG_1X1_BYTES
    finally:
        os.remove(out)


# === to_inline_blob ======================================================


def test_to_inline_blob_local_path_returns_mime_and_b64(tmp_path):
    _write_output_png(tmp_path, "uploads/ref.png")
    resolver = MediaResolver(FakeUploader(), project_root=str(tmp_path))
    mime, b64 = resolver.to_inline_blob("uploads/ref.png")
    assert mime == "image/png"
    assert base64.b64decode(b64) == PNG_1X1_BYTES


def test_to_inline_blob_object_key_uses_uploader_bytes():
    key = "manju-forge/users/1/storyboard/a.png"
    uploader = FakeUploader(
        configured=True, download_payload={key: PNG_1X1_BYTES}
    )
    mime, b64 = MediaResolver(uploader).to_inline_blob(key)
    assert mime == "image/png"
    assert base64.b64decode(b64) == PNG_1X1_BYTES


def test_to_inline_blob_data_uri_round_trips():
    data_uri = f"data:image/jpeg;base64,{PNG_1X1_BASE64}"
    mime, b64 = MediaResolver(FakeUploader()).to_inline_blob(data_uri)
    assert mime == "image/jpeg"
    assert b64 == PNG_1X1_BASE64
