"""Cartesia Text-to-Speech client (vendor-direct).

Used when the project's TTS instance has ``vendor_id == "cartesia"``.
Cartesia Sonic 3 is the lowest-latency TTS available in 2026 (~40-90ms
first byte) — ideal for voice agents and live narration.

API surface:
    POST {base}/tts/bytes
    Cartesia-Version: 2024-11-13
    X-API-Key: <CARTESIA_API_KEY>
    Body: {
        "model_id": "sonic-3",
        "transcript": "...",
        "voice": {"mode": "id", "id": "<voice id>"},
        "output_format": {
            "container": "mp3",
            "bit_rate": 128000,
            "sample_rate": 44100
        },
        "language": "en",
        "speed": "normal"          # "slow" | "normal" | "fast" | float -1..1
    }
    → returns audio bytes directly.
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


_DEFAULT_BASE_URL = "https://api.cartesia.ai"
_DEFAULT_MODEL = "sonic-3"
_DEFAULT_VOICE_ID = "a0e99841-438c-4a64-b679-ae501e7d6091"  # public catalog default
_API_VERSION = "2024-11-13"


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        v = inst.credentials.get("CARTESIA_API_KEY") or inst.credentials.get("OPENAI_API_KEY")
        if v:
            return v
    return get_cred("CARTESIA_API_KEY")


def _resolve_model(default: str = _DEFAULT_MODEL) -> str:
    inst = current_instance()
    if inst and inst.model_name:
        return inst.model_name
    return default


def _speed_label(rate: float) -> str:
    """Map our 0.5–2.0 multiplier to Cartesia's discrete labels."""
    if rate <= 0.85:
        return "slow"
    if rate >= 1.15:
        return "fast"
    return "normal"


def synthesize_cartesia_tts(
    text: str,
    output_path: str,
    *,
    voice: str,
    speech_rate: float = 1.0,
    pitch_rate: float = 1.0,
    volume: int = 50,
    audio_format: str = "mp3",
    sample_rate: int = 44100,
    language: str = "en",
) -> Tuple[str, float, str]:
    """Synthesize speech via Cartesia Sonic.

    Returns ``(output_path, latency_ms, request_id)`` to match the contract
    of :class:`TTSProcessor.synthesize`.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Cartesia TTS requires CARTESIA_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    model = _resolve_model()
    voice_id = voice or _DEFAULT_VOICE_ID

    output_format: dict = {
        "container": "mp3" if audio_format == "mp3" else "wav",
        "sample_rate": sample_rate,
    }
    if audio_format == "mp3":
        output_format["bit_rate"] = 128000
    else:
        output_format["encoding"] = "pcm_s16le"

    payload = {
        "model_id": model,
        "transcript": text,
        "voice": {"mode": "id", "id": voice_id},
        "output_format": output_format,
        "language": language,
        "speed": _speed_label(speech_rate),
    }
    headers = {
        "X-API-Key": api_key,
        "Cartesia-Version": _API_VERSION,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg" if audio_format == "mp3" else "audio/wav",
    }

    start = time.time()
    request_id = uuid.uuid4().hex
    logger.info(
        "Cartesia TTS request id=%s model=%s voice=%s len=%d",
        request_id, model, voice_id, len(text),
    )
    response = requests.post(f"{base}/tts/bytes", json=payload, headers=headers, timeout=120)
    if response.status_code != 200:
        try:
            err = response.json()
        except Exception:
            err = {"detail": response.text}
        raise RuntimeError(f"Cartesia TTS error: {err}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    latency_ms = (time.time() - start) * 1000
    logger.info(
        "Cartesia TTS done id=%s latency=%.0fms -> %s", request_id, latency_ms, output_path,
    )
    return output_path, latency_ms, request_id


__all__ = ["synthesize_cartesia_tts"]
