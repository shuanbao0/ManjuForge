"""Fish Audio Text-to-Speech client (vendor-direct).

Used when the project's TTS instance has ``vendor_id == "fish-audio"``.
Fish Audio's HTTP API serves speech synthesis with a ``reference_id`` that
points to either a built-in voice or a user-cloned voice.

API surface:
    POST {base}/v1/tts
    Authorization: Bearer <FISH_AUDIO_API_KEY>
    Body: {
        "text": "...",
        "reference_id": "<voice id>",
        "format": "mp3",                # "mp3" | "wav" | "pcm" | "opus"
        "mp3_bitrate": 128,
        "model": "s2",                  # "s2" (latest) | "s1"
        "chunk_length": 200,
        "normalize": true,
        "latency": "normal"
    }
    → returns audio bytes directly (Content-Type matches the format).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Optional, Tuple

import requests

from src.runtime import current_instance, get_cred

logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://api.fish.audio/v1"
_DEFAULT_MODEL = "s2"


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        v = inst.credentials.get("FISH_AUDIO_API_KEY") or inst.credentials.get("OPENAI_API_KEY")
        if v:
            return v
    return get_cred("FISH_AUDIO_API_KEY")


def _resolve_model(default: str = _DEFAULT_MODEL) -> str:
    inst = current_instance()
    if inst and inst.model_name:
        # Fish Audio model ids may carry our internal "fish-" prefix
        # (fish-s2 / fish-s1) — strip it before sending.
        name = inst.model_name
        if name.startswith("fish-"):
            return name[5:]
        return name
    return default


def synthesize_fish_tts(
    text: str,
    output_path: str,
    *,
    voice: str,
    speech_rate: float = 1.0,
    pitch_rate: float = 1.0,
    volume: int = 50,
    audio_format: str = "mp3",
    sample_rate: int = 44100,
) -> Tuple[str, float, str]:
    """Synthesize speech via Fish Audio.

    ``voice`` is a Fish Audio ``reference_id`` (built-in catalog id or a
    user-uploaded clone). Returns ``(output_path, latency_ms, request_id)``
    matching :class:`TTSProcessor.synthesize`.

    Note: speech_rate/pitch_rate/volume are not directly exposed by the
    Fish HTTP API today; they're carried for interface symmetry and may be
    honored once the API surface adds them. For now they only influence
    the chunk length heuristic.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Fish Audio TTS requires FISH_AUDIO_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    model = _resolve_model()

    payload: dict = {
        "text": text,
        "format": audio_format,
        "mp3_bitrate": 128,
        "model": model,
        "normalize": True,
        "latency": "normal",
        "chunk_length": 200,
    }
    if voice:
        payload["reference_id"] = voice
    if audio_format == "wav":
        payload["sample_rate"] = sample_rate

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "pcm": "audio/pcm",
            "opus": "audio/ogg",
        }.get(audio_format, "audio/mpeg"),
    }

    start = time.time()
    request_id = uuid.uuid4().hex
    logger.info(
        "Fish Audio TTS request id=%s model=%s voice=%s len=%d",
        request_id, model, voice or "<none>", len(text),
    )
    response = requests.post(f"{base}/tts", json=payload, headers=headers, timeout=180)
    if response.status_code != 200:
        try:
            err = response.json()
        except Exception:
            err = {"detail": response.text}
        raise RuntimeError(f"Fish Audio TTS error: {err}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    latency_ms = (time.time() - start) * 1000
    logger.info(
        "Fish Audio TTS done id=%s latency=%.0fms -> %s", request_id, latency_ms, output_path,
    )
    return output_path, latency_ms, request_id


__all__ = ["synthesize_fish_tts"]
