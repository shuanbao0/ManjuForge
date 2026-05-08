"""MiniMax image-01 client (T2I).

POST {base_url}/image_generation
Body:
    {
        "model": "image-01",
        "prompt": "...",
        "aspect_ratio": "1:1",     # or "16:9", "9:16", "3:2", ...
        "n": 1,                    # 1–9 images
        "response_format": "url"   # or "base64"
    }
Auth:
    Authorization: Bearer <MINIMAX_API_KEY>
"""
from __future__ import annotations

import io
import logging
import os
import time
from typing import List, Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        for key in ("MINIMAX_API_KEY", "OPENAI_API_KEY"):
            v = inst.credentials.get(key)
            if v:
                return v
    return get_cred("MINIMAX_API_KEY") or get_cred("OPENAI_API_KEY")


def _resolve_model(default: str = "image-01") -> str:
    inst = current_instance()
    if inst and inst.model_name:
        return inst.model_name
    return default


# Map ManjuForge size strings ("1024*1024") to MiniMax aspect_ratio strings.
def _size_to_aspect(size: str) -> str:
    if not size or "*" not in size:
        return "1:1"
    try:
        w, h = (int(x) for x in size.split("*"))
    except ValueError:
        return "1:1"
    ratios = [
        ("16:9", 16 / 9), ("9:16", 9 / 16), ("4:3", 4 / 3), ("3:4", 3 / 4),
        ("3:2", 3 / 2), ("2:3", 2 / 3), ("21:9", 21 / 9), ("1:1", 1.0),
    ]
    target = w / h
    return min(ratios, key=lambda r: abs(r[1] - target))[0]


def generate_minimax_image(
    prompt: str,
    output_path: str,
    *,
    size: str = "1024*1024",
    n: int = 1,
    negative_prompt: Optional[str] = None,
) -> Tuple[List[str], float]:
    """Run T2I on MiniMax image-01.

    Saves the first image to ``output_path``. Returns ``(saved_paths,
    api_latency_seconds)`` — saved_paths has length ``n`` for batch
    generation, named ``<output_path>_0.<ext>`` etc.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("MiniMax image generation requires MINIMAX_API_KEY in the active instance")
    base = _resolve_base_url()
    model = _resolve_model()

    payload = {
        "model": model,
        "prompt": prompt,
        "aspect_ratio": _size_to_aspect(size),
        "n": max(1, min(9, n)),
        "response_format": "url",
    }
    if negative_prompt:
        # MiniMax accepts negative_prompt as a top-level optional field.
        payload["negative_prompt"] = negative_prompt

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    logger.info("MiniMax T2I model=%s aspect=%s n=%d", model, payload["aspect_ratio"], payload["n"])
    response = requests.post(f"{base}/image_generation", json=payload, headers=headers, timeout=180)
    response.raise_for_status()
    body = response.json()
    api_latency = time.time() - start

    base_resp = body.get("base_resp", {})
    if base_resp.get("status_code") not in (0, None):
        raise RuntimeError(f"MiniMax image error: {base_resp}")

    image_urls = (body.get("data", {}) or {}).get("image_urls") or body.get("image_urls") or []
    if not image_urls:
        raise RuntimeError(f"MiniMax image returned no urls: {body}")

    saved: List[str] = []
    base_dir = os.path.dirname(output_path)
    base_name, ext = os.path.splitext(os.path.basename(output_path))
    if not ext:
        ext = ".png"
    os.makedirs(base_dir, exist_ok=True)

    for i, url in enumerate(image_urls):
        target = output_path if i == 0 and len(image_urls) == 1 else os.path.join(base_dir, f"{base_name}_{i}{ext}")
        # Download the image bytes and save locally.
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        with open(target, "wb") as f:
            f.write(r.content)
        saved.append(target)
    logger.info("MiniMax T2I saved %d files in %.2fs", len(saved), api_latency)
    return saved, api_latency


__all__ = ["generate_minimax_image"]
