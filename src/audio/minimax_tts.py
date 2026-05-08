"""MiniMax T2A v2 client (https://platform.minimax.io/docs/api-reference/speech-t2a-http).

Used when the project's TTS instance has ``vendor_id == "minimax"``. Hits the
non-streaming JSON endpoint at ``{base_url}/t2a_v2`` and saves the
hex-encoded audio bytes to ``output_path``.

API surface (subset we need):
    POST /v1/t2a_v2
    Authorization: Bearer <MINIMAX_API_KEY>
    Body: {
        "model": "speech-2.6-hd",
        "text": "...",
        "voice_setting": {
            "voice_id": "Wise_Woman",      # MiniMax voice id
            "speed": 1.0,                  # 0.5–2.0
            "vol": 1.0,                    # 0–10
            "pitch": 0,                    # -12–12 (semitones)
        },
        "audio_setting": {
            "sample_rate": 32000,
            "format": "mp3"                # "mp3" | "wav" | "pcm"
        }
    }
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


def _resolve_model(default: str = "speech-2.6-hd") -> str:
    inst = current_instance()
    if inst and inst.model_name:
        return inst.model_name
    return default


def synthesize_minimax_tts(
    text: str,
    output_path: str,
    *,
    voice: str,
    speech_rate: float = 1.0,
    pitch_rate: float = 1.0,
    volume: int = 50,
    audio_format: str = "mp3",
    sample_rate: int = 32000,
) -> Tuple[str, float, str]:
    """Synthesize speech via MiniMax T2A v2.

    Returns ``(output_path, latency_ms, request_id)`` to match the shape
    of :class:`TTSProcessor.synthesize` so the caller doesn't branch.

    Voice IDs differ from CosyVoice. MiniMax accepts its own voice catalog
    (``Wise_Woman`` / ``Calm_Woman`` / ``Patient_Man`` / ...). The user's
    project-level voice binding stores the picked id verbatim.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("MiniMax TTS requires MINIMAX_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    model = _resolve_model()

    # Volume on MiniMax is 0–10 (float); our pipeline passes 0–100 (int).
    minimax_volume = max(0.1, min(10.0, volume / 10.0))
    # Pitch on MiniMax is -12..+12 semitones; our pipeline passes 0.5–2.0
    # (multiplier). Map: 1.0 → 0, 0.5 → -12, 2.0 → +12 (rough log mapping).
    import math
    minimax_pitch = max(-12, min(12, int(round(12 * math.log2(max(0.01, pitch_rate))))))
    minimax_speed = max(0.5, min(2.0, speech_rate))

    payload = {
        "model": model,
        "text": text,
        "voice_setting": {
            "voice_id": voice,
            "speed": minimax_speed,
            "vol": minimax_volume,
            "pitch": minimax_pitch,
        },
        "audio_setting": {
            "sample_rate": sample_rate,
            "format": audio_format,
        },
        # Default stream=false so we get a single JSON response with hex audio.
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    request_id = uuid.uuid4().hex
    logger.info("MiniMax TTS request id=%s model=%s voice=%s len=%d", request_id, model, voice, len(text))
    response = requests.post(f"{base}/t2a_v2", json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    body = response.json()

    base_resp = body.get("base_resp", {})
    if base_resp.get("status_code") not in (0, None):
        raise RuntimeError(f"MiniMax TTS error: {base_resp}")

    audio_hex = body.get("data", {}).get("audio")
    if not audio_hex:
        raise RuntimeError(f"MiniMax TTS returned no audio payload: {body}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(bytes.fromhex(audio_hex))

    latency_ms = (time.time() - start) * 1000
    logger.info(
        "MiniMax TTS done id=%s latency=%.0fms -> %s", request_id, latency_ms, output_path
    )
    return output_path, latency_ms, request_id


__all__ = ["synthesize_minimax_tts"]
