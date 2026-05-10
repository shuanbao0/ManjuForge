"""MiniMax Hailuo video generation client (vendor-direct).

Implements the async task flow:
    POST {base}/video_generation                 → returns task_id
    GET  {base}/query/video_generation?task_id=  → poll until ``Success``
    GET  {base}/files/retrieve?file_id=          → fetch downloadable URL

Auth: ``Authorization: Bearer <MINIMAX_API_KEY>``.

Model ids (matching the wizard's suggestions):
    MiniMax-Hailuo-2.3-Fast / MiniMax-Hailuo-2.3 / MiniMax-Hailuo-02

The pipeline calls this via :class:`src.models.video_dispatcher.HailuoVendorAdapter`,
which is registered for ``("hailuo-", "vendor")``.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"
_POLL_INTERVAL_S = 4.0
_POLL_TIMEOUT_S = 600.0  # 10 min


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        for key in ("MINIMAX_API_KEY", "HAILUO_API_KEY", "OPENAI_API_KEY"):
            v = inst.credentials.get(key)
            if v:
                return v
    return get_cred("MINIMAX_API_KEY") or get_cred("HAILUO_API_KEY")


def _resolve_model(override: Optional[str] = None) -> str:
    from .instance import InstanceType, required_model_name
    return required_model_name(InstanceType.I2V, override=override)


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def generate_hailuo_video(
    *,
    prompt: str,
    output_path: str,
    img_url: Optional[str] = None,
    img_path: Optional[str] = None,
    duration: int = 6,
    resolution: str = "768P",
    model: Optional[str] = None,
) -> Tuple[str, float]:
    """Submit an i2v / t2v task and poll until done. Saves the MP4 to
    ``output_path`` and returns ``(output_path, total_seconds)``."""
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Hailuo video requires MINIMAX_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    target_model = _resolve_model(override=model)

    payload: dict = {
        "model": target_model,
        "prompt": prompt or "",
        "duration": int(duration or 6),
        "resolution": resolution,
    }
    # Frame source: prefer a public URL when handed out (OSS), else inline
    # the bytes as a data URI. Object keys + local paths both flow through
    # the resolver so the call still works under internal-only storage.
    ref = img_url or img_path
    if ref:
        from ..utils.provider_media import MediaResolver
        payload["first_frame_image"] = MediaResolver().to_url_or_inline(ref)

    started = time.time()
    logger.info("Hailuo submit model=%s duration=%ds resolution=%s", target_model, duration, resolution)
    submit = requests.post(f"{base}/video_generation", json=payload, headers=_headers(api_key), timeout=120)
    submit.raise_for_status()
    body = submit.json()
    base_resp = body.get("base_resp", {})
    if base_resp.get("status_code") not in (0, None):
        raise RuntimeError(f"Hailuo submit error: {base_resp}")

    task_id = body.get("task_id") or body.get("data", {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"Hailuo submit returned no task_id: {body}")

    file_id = _poll_until_done(base, api_key, task_id)
    download_url = _retrieve_file_url(base, api_key, file_id)
    _download_to(download_url, output_path)

    elapsed = time.time() - started
    logger.info("Hailuo done task=%s in %.1fs -> %s", task_id, elapsed, output_path)
    return output_path, elapsed


def _poll_until_done(base: str, api_key: str, task_id: str) -> str:
    deadline = time.time() + _POLL_TIMEOUT_S
    while time.time() < deadline:
        r = requests.get(
            f"{base}/query/video_generation",
            params={"task_id": task_id},
            headers=_headers(api_key),
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        status = (body.get("status") or body.get("data", {}).get("status") or "").lower()
        if status in ("success", "succeeded", "complete", "completed"):
            file_id = body.get("file_id") or body.get("data", {}).get("file_id")
            if not file_id:
                raise RuntimeError(f"Hailuo task succeeded but no file_id: {body}")
            return file_id
        if status in ("fail", "failed", "error"):
            raise RuntimeError(f"Hailuo task failed: {body}")
        logger.debug("Hailuo task=%s status=%s, polling again", task_id, status)
        time.sleep(_POLL_INTERVAL_S)
    raise TimeoutError(f"Hailuo task {task_id} did not complete within {_POLL_TIMEOUT_S}s")


def _retrieve_file_url(base: str, api_key: str, file_id: str) -> str:
    r = requests.get(
        f"{base}/files/retrieve",
        params={"file_id": file_id},
        headers=_headers(api_key),
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    url = body.get("file", {}).get("download_url") or body.get("data", {}).get("download_url")
    if not url:
        raise RuntimeError(f"Hailuo file retrieve returned no download_url: {body}")
    return url


def _download_to(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)


__all__ = ["generate_hailuo_video"]
