"""ByteDance Seedream image client (vendor-direct, Volcano Engine Ark).

Used when the project's T2I/I2I instance has ``vendor_id == "doubao"`` and
the active model id starts with ``doubao-seedream-``. Seedream is the
image companion to Seedance and shares the same Volcano account /
``DOUBAO_API_KEY``.

API surface (Volcano Engine OpenAI-compatible images endpoint):
    POST {base}/images/generations
    Authorization: Bearer <DOUBAO_API_KEY>
    Body: {
        "model": "doubao-seedream-3-0-t2i-250415",
        "prompt": "...",
        "size": "1024x1024",
        "n": 1,
        "response_format": "url",
        "image": "<data url or http url>"  # optional, enables I2I
    }

The client returns ``(saved_paths, api_latency_seconds)`` to match
:func:`src.models.minimax_image.generate_minimax_image` so the
``_route_for_call`` adapter can treat them the same way.
"""
from __future__ import annotations

import base64
import logging
import os
import time
from typing import List, Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
_DEFAULT_MODEL = "doubao-seedream-3-0-t2i-250415"


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


def _resolve_model(default: str = _DEFAULT_MODEL) -> str:
    inst = current_instance()
    if inst and inst.model_name:
        return inst.model_name
    return default


def _size_for_seedream(size: str) -> str:
    """Convert ManjuForge's ``WxH`` (with ``*``) to Seedream's ``WxH`` (with ``x``)."""
    if not size or "*" not in size:
        return "1024x1024"
    try:
        w, h = (int(x) for x in size.split("*"))
    except ValueError:
        return "1024x1024"
    return f"{w}x{h}"


def generate_seedream_image(
    prompt: str,
    output_path: str,
    *,
    size: str = "1024*1024",
    n: int = 1,
    negative_prompt: Optional[str] = None,
    ref_image_paths: Optional[List[str]] = None,
) -> Tuple[List[str], float]:
    """Run T2I or I2I on ByteDance Seedream.

    Saves the first image to ``output_path``; for ``n > 1`` returns
    ``output_path_0.<ext>`` etc. ``ref_image_paths`` enables I2I — only
    the first reference is used (Seedream API takes a single ``image``).
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Seedream image generation requires DOUBAO_API_KEY in the active instance")
    base = _resolve_base_url()
    model = _resolve_model()

    payload: dict = {
        "model": model,
        "prompt": prompt,
        "size": _size_for_seedream(size),
        "n": max(1, min(4, n)),
        "response_format": "url",
        "watermark": False,
    }
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    if ref_image_paths:
        first_ref = next((p for p in ref_image_paths if p), None)
        if first_ref:
            from ..utils.provider_media import MediaResolver
            payload["image"] = MediaResolver().to_url_or_inline(first_ref)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    logger.info("Seedream model=%s size=%s n=%d ref=%s", model, payload["size"], payload["n"], bool(ref_image_paths))
    response = requests.post(f"{base}/images/generations", json=payload, headers=headers, timeout=300)
    if response.status_code != 200:
        try:
            err = response.json()
        except Exception:
            err = {"detail": response.text}
        raise RuntimeError(f"Seedream error: {err}")
    body = response.json()
    api_latency = time.time() - start

    data = body.get("data", []) or []
    if not data:
        raise RuntimeError(f"Seedream returned no images: {body}")

    saved: List[str] = []
    base_dir = os.path.dirname(output_path)
    base_name, ext = os.path.splitext(os.path.basename(output_path))
    if not ext:
        ext = ".png"
    os.makedirs(base_dir, exist_ok=True)

    for i, item in enumerate(data):
        url = item.get("url") or item.get("b64_json")
        if not url:
            continue
        target = output_path if i == 0 and len(data) == 1 else os.path.join(base_dir, f"{base_name}_{i}{ext}")
        if url.startswith("http"):
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(target, "wb") as f:
                f.write(r.content)
        else:
            with open(target, "wb") as f:
                f.write(base64.b64decode(url))
        saved.append(target)

    logger.info("Seedream saved %d files in %.2fs", len(saved), api_latency)
    return saved, api_latency


__all__ = ["generate_seedream_image"]
