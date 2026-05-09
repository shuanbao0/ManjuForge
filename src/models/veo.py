"""Google Veo 3.1 video client (vendor-direct, Gemini API).

Used when the project's I2V/T2V instance has ``vendor_id == "google"`` and
the active model id starts with ``veo-``. Veo is invoked through
Gemini's long-running operation API: submit a request, poll the
operation, then download the returned video file.

API surface:
    POST {base}/v1beta/models/{model}:predictLongRunning
    Header: x-goog-api-key: <GOOGLE_API_KEY>
    Body: {
        "instances": [{
            "prompt": "...",
            "image": {"bytesBase64Encoded": "...", "mimeType": "image/png"}
        }],
        "parameters": {
            "aspectRatio": "16:9",
            "durationSeconds": 8,
            "resolution": "1080p"
        }
    }
    → { "name": "models/.../operations/..." }

    GET {base}/v1beta/{operation_name}
    → { "done": true, "response": { "generateVideoResponse": { "generatedSamples":
        [{ "video": { "uri": "https://generativelanguage.googleapis.com/..." } }] } } }

    Final video download requires the API key as a ``key`` query param.
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


_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
_DEFAULT_MODEL = "veo-3.1-generate-preview"
_POLL_INTERVAL_S = 6.0
_POLL_TIMEOUT_S = 900.0  # 15 min — Veo can take several minutes


_MODEL_ID_MAP = {
    "veo-3.1": "veo-3.1-generate-preview",
    "veo-3.1-fast": "veo-3.1-fast-generate-preview",
    "veo-3": "veo-3.0-generate-001",
    "veo-3-fast": "veo-3.0-fast-generate-001",
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


def _resolve_model(default: str = _DEFAULT_MODEL, override: Optional[str] = None) -> str:
    name = override
    if not name:
        inst = current_instance()
        if inst and inst.model_name:
            name = inst.model_name
    name = name or default
    return _MODEL_ID_MAP.get(name, name)


def _encode_local_image(local_path: str) -> dict:
    mime, _ = mimetypes.guess_type(local_path)
    mime = mime or "image/png"
    with open(local_path, "rb") as f:
        return {
            "bytesBase64Encoded": base64.b64encode(f.read()).decode("ascii"),
            "mimeType": mime,
        }


def _aspect_for_resolution(resolution: str) -> str:
    # Veo only formally supports 16:9 and 9:16 today.
    if resolution and resolution.lower() in ("vertical", "portrait"):
        return "9:16"
    return "16:9"


def generate_veo_video(
    *,
    prompt: str,
    output_path: str,
    img_url: Optional[str] = None,
    img_path: Optional[str] = None,
    duration: int = 8,
    resolution: str = "1080p",
    model: Optional[str] = None,
) -> Tuple[str, float]:
    """Submit a Veo job, poll until done, save the MP4 to ``output_path``."""
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Veo requires GOOGLE_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    target_model = _resolve_model(override=model)

    instance: dict = {"prompt": prompt or ""}
    if img_url and img_url.startswith("http"):
        # Veo accepts ``imageUri`` for HTTP-fetchable images directly.
        instance["image"] = {"imageUri": img_url}
    elif img_path and os.path.exists(img_path):
        instance["image"] = _encode_local_image(img_path)

    parameters = {
        "aspectRatio": _aspect_for_resolution(resolution),
        "durationSeconds": int(duration or 8),
        "resolution": (resolution or "1080p").lower(),
        "personGeneration": "allow_adult",
    }
    payload = {"instances": [instance], "parameters": parameters}

    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    start = time.time()
    logger.info("Veo submit model=%s aspect=%s duration=%ds", target_model, parameters["aspectRatio"], parameters["durationSeconds"])
    submit = requests.post(
        f"{base}/v1beta/models/{target_model}:predictLongRunning",
        json=payload, headers=headers, timeout=120,
    )
    if submit.status_code != 200:
        try:
            err = submit.json()
        except Exception:
            err = {"detail": submit.text}
        raise RuntimeError(f"Veo submit error: {err}")
    op = submit.json()
    op_name = op.get("name")
    if not op_name:
        raise RuntimeError(f"Veo submit returned no operation name: {op}")

    sample = _poll_operation(base, api_key, op_name)
    video_uri = sample.get("video", {}).get("uri") or sample.get("uri") or sample.get("videoUri")
    if not video_uri:
        raise RuntimeError(f"Veo operation done but no video uri: {sample}")

    _download(video_uri, output_path, api_key)

    elapsed = time.time() - start
    logger.info("Veo done in %.1fs -> %s", elapsed, output_path)
    return output_path, elapsed


def _poll_operation(base: str, api_key: str, op_name: str) -> dict:
    deadline = time.time() + _POLL_TIMEOUT_S
    headers = {"x-goog-api-key": api_key}
    url = f"{base}/v1beta/{op_name.lstrip('/')}"
    while time.time() < deadline:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        body = r.json()
        if body.get("done"):
            if "error" in body and body["error"]:
                raise RuntimeError(f"Veo operation failed: {body['error']}")
            response = body.get("response") or {}
            samples = (
                ((response.get("generateVideoResponse") or {}).get("generatedSamples"))
                or response.get("generatedSamples")
                or response.get("videos")
                or []
            )
            if not samples:
                raise RuntimeError(f"Veo done but no samples: {body}")
            return samples[0]
        time.sleep(_POLL_INTERVAL_S)
    raise TimeoutError(f"Veo operation {op_name} did not complete within {_POLL_TIMEOUT_S}s")


def _download(uri: str, output_path: str, api_key: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # Gemini-served videos require the API key as a query param.
    sep = "&" if "?" in uri else "?"
    download_url = uri if "key=" in uri else f"{uri}{sep}key={api_key}"
    with requests.get(download_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)


__all__ = ["generate_veo_video"]
