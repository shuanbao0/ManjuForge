"""ByteDance Seedance video client (vendor-direct, Volcano Engine Ark).

Used when the project's I2V/T2V instance has ``vendor_id == "doubao"`` and
the active model id starts with ``doubao-seedance-``. Seedance 2.0 (2026-02)
shipped multi-shot storytelling and joint audio-video generation; this
client routes any of the 1.0 / 1.5 / 2.0 ids through the same Ark
``content_generation.tasks`` API.

API surface (Volcano Engine Ark):
    POST {base}/contents/generations/tasks
    Authorization: Bearer <DOUBAO_API_KEY>
    Body: {
        "model": "doubao-seedance-2-0-pro-...",
        "content": [
            {"type": "text", "text": "<prompt> --resolution 1080p --duration 5"},
            {"type": "image_url", "image_url": {"url": "<data url or http url>"}}
        ]
    }
    → returns { "id": "task_..." }

    GET {base}/contents/generations/tasks/{id}
    → status: queued | running | succeeded | failed
       on success: content.video_url is downloadable.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import time
from typing import Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
_DEFAULT_MODEL = "doubao-seedance-1-0-pro-fast-251015"
_POLL_INTERVAL_S = 4.0
_POLL_TIMEOUT_S = 900.0  # 15 min


# Map our user-facing catalog ids → Volcano Engine model_name. Keep this
# narrow; advanced users can punch a raw API id via the instance row.
_MODEL_ID_MAP = {
    "doubao-seedance-2.0-pro": "doubao-seedance-2-0-pro-260215",
    "doubao-seedance-2.0": "doubao-seedance-2-0-260215",
    "doubao-seedance-1.5-pro": "doubao-seedance-1-5-pro-fast-251015",
    "doubao-seedance-1.0-pro": "doubao-seedance-1-0-pro-fast-251015",
}


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        v = inst.credentials.get("DOUBAO_API_KEY") or inst.credentials.get("ARK_API_KEY")
        if v:
            return v
    return get_cred("DOUBAO_API_KEY") or get_cred("ARK_API_KEY")


def _resolve_model(override: Optional[str] = None) -> str:
    name = override
    if not name:
        inst = current_instance()
        if inst and inst.model_name:
            name = inst.model_name
    name = name or _DEFAULT_MODEL
    return _MODEL_ID_MAP.get(name, name)


def _encode_image_data_url(local_path: str) -> str:
    mime, _ = mimetypes.guess_type(local_path)
    mime = mime or "image/png"
    with open(local_path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode('ascii')}"


def generate_seedance_video(
    *,
    prompt: str,
    output_path: str,
    img_url: Optional[str] = None,
    img_path: Optional[str] = None,
    duration: int = 5,
    resolution: str = "1080p",
    model: Optional[str] = None,
) -> Tuple[str, float]:
    """Submit a Seedance task, poll, save the MP4 to ``output_path``."""
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Seedance requires DOUBAO_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    target_model = _resolve_model(override=model)

    # Seedance's prompt carries inline directives; appending --resolution
    # and --duration is the supported way to override the defaults.
    decorated = f"{prompt or ''} --resolution {resolution or '1080p'} --duration {int(duration or 5)} --watermark false"
    content = [{"type": "text", "text": decorated.strip()}]
    if img_url and img_url.startswith("http"):
        content.append({"type": "image_url", "image_url": {"url": img_url}})
    elif img_path and os.path.exists(img_path):
        content.append({"type": "image_url", "image_url": {"url": _encode_image_data_url(img_path)}})

    payload = {"model": target_model, "content": content}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    logger.info("Seedance submit model=%s duration=%ds resolution=%s", target_model, duration, resolution)
    submit = requests.post(
        f"{base}/contents/generations/tasks",
        json=payload, headers=headers, timeout=120,
    )
    if submit.status_code not in (200, 201):
        try:
            err = submit.json()
        except Exception:
            err = {"detail": submit.text}
        raise RuntimeError(f"Seedance submit error: {err}")
    body = submit.json()
    task_id = body.get("id") or body.get("task_id") or (body.get("data") or {}).get("id")
    if not task_id:
        raise RuntimeError(f"Seedance submit returned no task id: {body}")

    video_url = _poll_until_done(base, headers, task_id)
    _download(video_url, output_path)

    elapsed = time.time() - start
    logger.info("Seedance done task=%s in %.1fs -> %s", task_id, elapsed, output_path)
    return output_path, elapsed


def _poll_until_done(base: str, headers: dict, task_id: str) -> str:
    deadline = time.time() + _POLL_TIMEOUT_S
    while time.time() < deadline:
        r = requests.get(f"{base}/contents/generations/tasks/{task_id}", headers=headers, timeout=30)
        r.raise_for_status()
        body = r.json()
        status = (body.get("status") or "").lower()
        if status in ("succeeded", "success"):
            content = body.get("content") or {}
            url = content.get("video_url") or content.get("url")
            if not url:
                raise RuntimeError(f"Seedance succeeded but no video_url: {body}")
            return url
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"Seedance task {status}: {body.get('error') or body}")
        time.sleep(_POLL_INTERVAL_S)
    raise TimeoutError(f"Seedance task {task_id} did not complete within {_POLL_TIMEOUT_S}s")


def _download(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)


__all__ = ["generate_seedance_video"]
