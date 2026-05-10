"""Google Gemini Image (Nano Banana series) client.

Used when the project's T2I/I2I instance has ``vendor_id == "google"`` and
the active model id starts with ``gemini-`` or ``nano-banana``. Gemini's
image generation accepts up to 14 reference image parts in a single call,
which makes it ManjuForge's strongest current option for character
consistency in storyboards (Apr 2026 benchmarks).

API surface:
    POST {base}/v1beta/models/{model}:generateContent
    Header: x-goog-api-key: <GOOGLE_API_KEY>
    Body: {
        "contents": [{"parts": [
            {"text": "..."},
            {"inline_data": {"mime_type": "image/png", "data": "<base64>"}}
        ]}],
        "generationConfig": {"responseModalities": ["IMAGE"]}
    }
    → response.candidates[0].content.parts[*].inline_data.{mime_type,data}
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


_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
_DEFAULT_MODEL = "gemini-2.5-flash-image-preview"
_MAX_REF_IMAGES = 14


# Mapping from our user-facing catalog ids to Gemini's actual API ids.
# Keep this small — anything not in the map is sent through verbatim so
# advanced users can plug in newer models without a code change.
_MODEL_ID_MAP = {
    "gemini-3.1-flash-image": "gemini-3.1-flash-image-preview",
    "nano-banana-pro": "gemini-3-pro-image",
    "nano-banana-2": "gemini-3-flash-image",
    "nano-banana": "gemini-2.5-flash-image-preview",
}


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
            v = inst.credentials.get(key)
            if v:
                return v
    return get_cred("GOOGLE_API_KEY") or get_cred("GEMINI_API_KEY")


def _resolve_model(default: str = _DEFAULT_MODEL) -> str:
    inst = current_instance()
    if inst and inst.model_name:
        name = inst.model_name
        return _MODEL_ID_MAP.get(name, name)
    return default


def _ref_to_inline_part(ref: str) -> Optional[dict]:
    """Resolve any media ref (URL / local / OSS key / data URI) into a
    Gemini ``inline_data`` part. Gemini's image-generation API does not
    accept URLs for reference images, so every input is inlined as base64."""
    from ..utils.provider_media import MediaResolver
    try:
        mime, b64 = MediaResolver().to_inline_blob(ref)
    except Exception as e:  # pragma: no cover — network / OSS failure path
        logger.warning("Gemini Image: failed to inline reference %s: %s", ref, e)
        return None
    return {"inline_data": {"mime_type": mime, "data": b64}}


def generate_gemini_image(
    prompt: str,
    output_path: str,
    *,
    size: str = "1024*1024",
    n: int = 1,
    negative_prompt: Optional[str] = None,
    ref_image_paths: Optional[List[str]] = None,
) -> Tuple[List[str], float]:
    """Run T2I or multi-reference I2I on Gemini Image / Nano Banana.

    Up to 14 reference images are forwarded as ``inline_data`` parts.
    Gemini returns one image per call, so ``n > 1`` issues sequential
    calls. Negative prompt is folded into the text part since the API has
    no dedicated field today.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Gemini Image requires GOOGLE_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    model = _resolve_model()

    text = prompt
    if negative_prompt:
        text = f"{prompt}\n\nAvoid: {negative_prompt}"

    parts: List[dict] = [{"text": text}]
    if ref_image_paths:
        for ref in ref_image_paths[:_MAX_REF_IMAGES]:
            if not ref:
                continue
            part = _ref_to_inline_part(ref)
            if part:
                parts.append(part)

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
        },
    }
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    saved: List[str] = []
    base_dir = os.path.dirname(output_path)
    base_name, ext = os.path.splitext(os.path.basename(output_path))
    if not ext:
        ext = ".png"
    os.makedirs(base_dir, exist_ok=True)

    started = time.time()
    for i in range(max(1, n)):
        logger.info("Gemini Image model=%s ref_parts=%d sample=%d/%d", model, len(parts) - 1, i + 1, n)
        url = f"{base}/v1beta/models/{model}:generateContent"
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        if response.status_code != 200:
            try:
                err = response.json()
            except Exception:
                err = {"detail": response.text}
            raise RuntimeError(f"Gemini Image error: {err}")
        body = response.json()

        image_b64 = _extract_image(body)
        if not image_b64:
            raise RuntimeError(f"Gemini Image returned no image data: {body}")

        target = output_path if i == 0 and n == 1 else os.path.join(base_dir, f"{base_name}_{i}{ext}")
        with open(target, "wb") as f:
            f.write(base64.b64decode(image_b64))
        saved.append(target)

    elapsed = time.time() - started
    logger.info("Gemini Image saved %d files in %.2fs", len(saved), elapsed)
    return saved, elapsed


def _extract_image(body: dict) -> Optional[str]:
    candidates = body.get("candidates") or []
    if not candidates:
        return None
    parts = (candidates[0].get("content") or {}).get("parts") or []
    for part in parts:
        inline = part.get("inline_data") or part.get("inlineData")
        if inline and inline.get("data"):
            return inline["data"]
    return None


__all__ = ["generate_gemini_image"]
