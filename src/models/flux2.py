"""Black Forest Labs FLUX.2 image client (vendor-direct).

Used when the project's T2I/I2I instance has ``vendor_id == "bfl"``.
FLUX.2 supports up to 10 reference images for character / product
preservation — we forward whichever ``ref_image_paths`` the caller provides.

API surface (async task with polling):
    POST {base}/v1/<model>             → returns {"id": "...", "polling_url": "..."}
    GET  {polling_url}                 → poll until status == "Ready"
        body.result.sample is the image URL

Auth: ``x-key: <BFL_API_KEY>``.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import os
import time
from typing import List, Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://api.bfl.ai"
_DEFAULT_MODEL = "flux-2-pro"
_POLL_INTERVAL_S = 1.5
_POLL_TIMEOUT_S = 300.0


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        v = inst.credentials.get("BFL_API_KEY")
        if v:
            return v
    return get_cred("BFL_API_KEY")


def _resolve_model(default: str = _DEFAULT_MODEL) -> str:
    inst = current_instance()
    if inst and inst.model_name:
        return inst.model_name
    return default


def _aspect_for_size(size: str) -> str:
    """Map our ``WxH`` (with ``*``) to FLUX's ``aspect_ratio`` strings."""
    if not size or "*" not in size:
        return "1:1"
    try:
        w, h = (int(x) for x in size.split("*"))
    except ValueError:
        return "1:1"
    candidates = [
        ("16:9", 16 / 9), ("9:16", 9 / 16), ("4:3", 4 / 3), ("3:4", 3 / 4),
        ("3:2", 3 / 2), ("2:3", 2 / 3), ("21:9", 21 / 9), ("9:21", 9 / 21),
        ("1:1", 1.0),
    ]
    target = w / h
    return min(candidates, key=lambda r: abs(r[1] - target))[0]


def _to_base64(local_path: str) -> str:
    mime, _ = mimetypes.guess_type(local_path)
    mime = mime or "image/png"
    with open(local_path, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode('ascii')}"


def generate_flux2_image(
    prompt: str,
    output_path: str,
    *,
    size: str = "1024*1024",
    n: int = 1,
    negative_prompt: Optional[str] = None,
    ref_image_paths: Optional[List[str]] = None,
) -> Tuple[List[str], float]:
    """Run T2I or multi-reference I2I on FLUX.2.

    FLUX.2 returns one sample per request, so the ``n`` parameter is
    honored by issuing ``n`` parallel requests serially. Returns
    ``(saved_paths, total_latency_seconds)``.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("FLUX.2 requires BFL_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    model = _resolve_model()

    base_payload: dict = {
        "prompt": prompt,
        "aspect_ratio": _aspect_for_size(size),
        "output_format": "png",
        "safety_tolerance": 2,
    }
    if negative_prompt:
        base_payload["prompt_upsampling"] = False
    if ref_image_paths:
        encoded: List[str] = []
        for ref in ref_image_paths[:10]:  # FLUX.2 caps at 10 references
            if not ref:
                continue
            if ref.startswith("http"):
                encoded.append(ref)
            elif os.path.exists(ref):
                encoded.append(_to_base64(ref))
        if encoded:
            base_payload["image_prompts"] = encoded

    headers = {
        "x-key": api_key,
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    saved: List[str] = []
    base_dir = os.path.dirname(output_path)
    base_name, ext = os.path.splitext(os.path.basename(output_path))
    if not ext:
        ext = ".png"
    os.makedirs(base_dir, exist_ok=True)

    started = time.time()
    for i in range(max(1, n)):
        logger.info("FLUX.2 model=%s aspect=%s ref=%d sample=%d/%d",
                    model, base_payload["aspect_ratio"], len(base_payload.get("image_prompts", []) or []), i + 1, n)
        submit = requests.post(f"{base}/v1/{model}", json=base_payload, headers=headers, timeout=120)
        if submit.status_code != 200:
            try:
                err = submit.json()
            except Exception:
                err = {"detail": submit.text}
            raise RuntimeError(f"FLUX.2 submit error: {err}")
        body = submit.json()
        polling_url = body.get("polling_url")
        if not polling_url:
            raise RuntimeError(f"FLUX.2 submit returned no polling_url: {body}")

        sample_url = _poll_for_sample(polling_url, headers)
        target = output_path if i == 0 and n == 1 else os.path.join(base_dir, f"{base_name}_{i}{ext}")
        _download(sample_url, target)
        saved.append(target)

    elapsed = time.time() - started
    logger.info("FLUX.2 saved %d files in %.2fs", len(saved), elapsed)
    return saved, elapsed


def _poll_for_sample(polling_url: str, headers: dict) -> str:
    deadline = time.time() + _POLL_TIMEOUT_S
    while time.time() < deadline:
        r = requests.get(polling_url, headers=headers, timeout=30)
        r.raise_for_status()
        body = r.json()
        status = body.get("status", "")
        if status == "Ready":
            sample = (body.get("result") or {}).get("sample")
            if not sample:
                raise RuntimeError(f"FLUX.2 ready but no sample: {body}")
            return sample
        if status in ("Error", "Content Moderated", "Request Moderated", "Task not found"):
            raise RuntimeError(f"FLUX.2 task {status}: {body}")
        time.sleep(_POLL_INTERVAL_S)
    raise TimeoutError(f"FLUX.2 task did not complete within {_POLL_TIMEOUT_S}s")


def _download(url: str, target: str) -> None:
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with open(target, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)


__all__ = ["generate_flux2_image"]
