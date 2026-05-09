"""fal.ai aggregator client (T2I / I2I / I2V / T2V).

Used when the project's instance has ``vendor_id == "fal"``. fal.ai
brokers 600+ models behind one API key — Veo 3.1, Sora 2, Kling 3.0,
Seedance 1.5 Pro, FLUX.2 etc. The user picks a model id (e.g.
``fal-ai/veo-3.1`` or ``fal-veo-3.1`` which we map onto the canonical
fal endpoint).

All fal endpoints share the queue API:
    POST {base}/{model_path}                  → returns {"request_id": "..."}
    GET  {base}/{model_path}/status?request_id=...
    GET  {base}/{model_path}/result?request_id=...

Auth: ``Authorization: Key <FAL_API_KEY>``.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://queue.fal.run"
_POLL_INTERVAL_S = 2.0
_POLL_TIMEOUT_S = 900.0  # 15 min — large video jobs can take a while


# Map our catalog model ids → fal.ai endpoint paths. Kept narrow: every id
# we expose in InstanceWizard.tsx maps to a real fal endpoint.
_MODEL_PATH_MAP = {
    # Image
    "fal-flux-2-pro": "fal-ai/flux-2-pro/text-to-image",
    "fal-seedream-5.0": "fal-ai/seedream/v5/text-to-image",
    "fal-nano-banana-pro": "fal-ai/nano-banana-pro/text-to-image",
    "fal-gemini-3.1-flash-image": "fal-ai/gemini-3-flash-image/edit",
    # Video
    "fal-veo-3.1": "fal-ai/veo3.1/image-to-video",
    "fal-kling-3.0": "fal-ai/kling-video/v3/pro/image-to-video",
    "fal-seedance-1.5-pro": "fal-ai/bytedance/seedance/v1-5/pro/image-to-video",
}


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        v = inst.credentials.get("FAL_API_KEY")
        if v:
            return v
    return get_cred("FAL_API_KEY")


def _resolve_model_path(default_path: str) -> str:
    inst = current_instance()
    if inst and inst.model_name:
        name = inst.model_name
        return _MODEL_PATH_MAP.get(name, name if "/" in name else default_path)
    return default_path


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Key {api_key}",
        "Content-Type": "application/json",
    }


def _to_data_url(local_path: str) -> str:
    mime, _ = mimetypes.guess_type(local_path)
    mime = mime or "image/png"
    with open(local_path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode('ascii')}"


def _submit_and_wait(api_key: str, model_path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    base = _resolve_base_url()
    url = f"{base}/{model_path}"
    submit = requests.post(url, json=payload, headers=_headers(api_key), timeout=120)
    if submit.status_code not in (200, 202):
        try:
            err = submit.json()
        except Exception:
            err = {"detail": submit.text}
        raise RuntimeError(f"fal submit error: {err}")
    body = submit.json()
    request_id = body.get("request_id")
    if not request_id:
        # Some sync endpoints return the result directly.
        if body.get("images") or body.get("video") or body.get("audio"):
            return body
        raise RuntimeError(f"fal submit returned no request_id: {body}")

    deadline = time.time() + _POLL_TIMEOUT_S
    status_url = body.get("status_url") or f"{url}/requests/{request_id}/status"
    result_url = body.get("response_url") or f"{url}/requests/{request_id}"
    while time.time() < deadline:
        r = requests.get(status_url, headers=_headers(api_key), timeout=30)
        r.raise_for_status()
        status = (r.json().get("status") or "").upper()
        if status == "COMPLETED":
            res = requests.get(result_url, headers=_headers(api_key), timeout=60)
            res.raise_for_status()
            return res.json()
        if status in ("FAILED", "CANCELLED", "ERROR"):
            raise RuntimeError(f"fal task {status}: {r.json()}")
        time.sleep(_POLL_INTERVAL_S)
    raise TimeoutError(f"fal task {request_id} did not complete within {_POLL_TIMEOUT_S}s")


def _download(url: str, target: str) -> None:
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with requests.get(url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(target, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)


# ── Image (T2I / I2I) ────────────────────────────────────────────────────


def generate_fal_image(
    prompt: str,
    output_path: str,
    *,
    size: str = "1024*1024",
    n: int = 1,
    negative_prompt: Optional[str] = None,
    ref_image_paths: Optional[List[str]] = None,
) -> Tuple[List[str], float]:
    """T2I or I2I via fal.ai. Returns ``(saved_paths, latency_seconds)``."""
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("fal.ai requires FAL_API_KEY in the active instance credentials")

    model_path = _resolve_model_path("fal-ai/flux-2-pro/text-to-image")
    if ref_image_paths and "/text-to-image" in model_path:
        # Promote to image-to-image variant when reference images are provided.
        model_path = model_path.replace("/text-to-image", "/image-to-image")

    payload: Dict[str, Any] = {
        "prompt": prompt,
        "image_size": _fal_image_size(size),
        "num_images": max(1, min(4, n)),
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    if ref_image_paths:
        urls = [r if r.startswith("http") else _to_data_url(r) for r in ref_image_paths if r and (r.startswith("http") or os.path.exists(r))]
        if urls:
            payload["image_urls"] = urls[:10]
            payload["image_url"] = urls[0]  # legacy single-ref endpoints

    started = time.time()
    body = _submit_and_wait(api_key, model_path, payload)
    elapsed = time.time() - started

    images = body.get("images") or []
    if not images:
        raise RuntimeError(f"fal image returned no results: {body}")

    saved: List[str] = []
    base_dir = os.path.dirname(output_path)
    base_name, ext = os.path.splitext(os.path.basename(output_path))
    if not ext:
        ext = ".png"
    for i, item in enumerate(images):
        url = item.get("url")
        if not url:
            continue
        target = output_path if i == 0 and len(images) == 1 else os.path.join(base_dir, f"{base_name}_{i}{ext}")
        _download(url, target)
        saved.append(target)
    logger.info("fal image (%s) saved %d files in %.2fs", model_path, len(saved), elapsed)
    return saved, elapsed


def _fal_image_size(size: str) -> str:
    """fal accepts named buckets: square_hd, portrait_16_9, landscape_16_9, etc."""
    if not size or "*" not in size:
        return "square_hd"
    try:
        w, h = (int(x) for x in size.split("*"))
    except ValueError:
        return "square_hd"
    target = w / h
    candidates = [
        ("landscape_16_9", 16 / 9), ("portrait_16_9", 9 / 16),
        ("landscape_4_3", 4 / 3), ("portrait_4_3", 3 / 4),
        ("square_hd", 1.0),
    ]
    return min(candidates, key=lambda r: abs(r[1] - target))[0]


# ── Video (I2V / T2V) ────────────────────────────────────────────────────


def generate_fal_video(
    *,
    prompt: str,
    output_path: str,
    img_url: Optional[str] = None,
    img_path: Optional[str] = None,
    duration: int = 5,
    resolution: str = "720p",
    model: Optional[str] = None,
) -> Tuple[str, float]:
    """I2V or T2V via fal.ai. ``model`` overrides the active instance model
    when supplied; otherwise resolves from the bound ModelInstance."""
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("fal.ai requires FAL_API_KEY in the active instance credentials")
    if model:
        model_path = _MODEL_PATH_MAP.get(model, model if "/" in model else "fal-ai/veo3.1/image-to-video")
    else:
        model_path = _resolve_model_path("fal-ai/veo3.1/image-to-video")

    payload: Dict[str, Any] = {
        "prompt": prompt or "",
        "duration": int(duration or 5),
        "resolution": resolution or "720p",
    }
    if img_url and img_url.startswith("http"):
        payload["image_url"] = img_url
    elif img_path and os.path.exists(img_path):
        payload["image_url"] = _to_data_url(img_path)

    started = time.time()
    body = _submit_and_wait(api_key, model_path, payload)
    elapsed = time.time() - started

    video = body.get("video") or {}
    url = video.get("url") or body.get("video_url")
    if not url and isinstance(body.get("output"), dict):
        url = body["output"].get("video_url") or body["output"].get("url")
    if not url:
        raise RuntimeError(f"fal video returned no url: {body}")

    _download(url, output_path)
    logger.info("fal video (%s) saved in %.1fs -> %s", model_path, elapsed, output_path)
    return output_path, elapsed


__all__ = ["generate_fal_image", "generate_fal_video"]
