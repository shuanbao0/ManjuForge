"""ElevenLabs Text-to-Speech client (vendor-direct).

Used when the project's TTS instance has ``vendor_id == "elevenlabs"``.
ElevenLabs serves the requested ``model_id`` against a chosen voice id and
returns raw MP3 bytes.

API surface:
    POST {base}/v1/text-to-speech/{voice_id}
    xi-api-key: <ELEVENLABS_API_KEY>
    Body: {
        "text": "...",
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": true,
            "speed": 1.0
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


_DEFAULT_BASE_URL = "https://api.elevenlabs.io/v1"
# Sensible defaults — "Rachel" is a standard ElevenLabs library voice.
_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


def _resolve_base_url() -> str:
    inst = current_instance()
    if inst and inst.base_url:
        return inst.base_url.rstrip("/")
    return _DEFAULT_BASE_URL


def _resolve_api_key() -> str:
    inst = current_instance()
    if inst:
        v = inst.credentials.get("ELEVENLABS_API_KEY") or inst.credentials.get("OPENAI_API_KEY")
        if v:
            return v
    return get_cred("ELEVENLABS_API_KEY")


def _resolve_model() -> str:
    from src.models.instance import InstanceType, required_model_name
    return required_model_name(InstanceType.TTS)


def synthesize_elevenlabs_tts(
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
    """Synthesize speech via ElevenLabs.

    Returns ``(output_path, latency_ms, request_id)`` to match the contract
    of :class:`TTSProcessor.synthesize` so the caller does not branch.

    ``voice`` is the ElevenLabs voice id (24-char hex like ``21m00Tcm4...``).
    Falls back to the Rachel default when empty so first-time users still
    hear something.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("ElevenLabs TTS requires ELEVENLABS_API_KEY in the active instance credentials")
    base = _resolve_base_url()
    model = _resolve_model()
    voice_id = voice or _DEFAULT_VOICE_ID

    # ElevenLabs voice_settings.speed accepts 0.7–1.2 only on supported
    # models; stay inside that range. We map our 0.5–2.0 input via clamp.
    el_speed = max(0.7, min(1.2, speech_rate))

    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
            "speed": el_speed,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg" if audio_format == "mp3" else "audio/wav",
    }

    output_format = {
        "mp3": f"mp3_{sample_rate}_128",
        "wav": f"pcm_{sample_rate}",
    }.get(audio_format, "mp3_44100_128")

    start = time.time()
    request_id = uuid.uuid4().hex
    logger.info(
        "ElevenLabs TTS request id=%s model=%s voice=%s len=%d",
        request_id, model, voice_id, len(text),
    )
    response = requests.post(
        f"{base}/text-to-speech/{voice_id}",
        params={"output_format": output_format},
        json=payload,
        headers=headers,
        timeout=120,
    )
    if response.status_code != 200:
        # ElevenLabs returns JSON on error; keep the message for the user.
        try:
            err = response.json()
        except Exception:
            err = {"detail": response.text}
        raise RuntimeError(f"ElevenLabs TTS error: {err}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    latency_ms = (time.time() - start) * 1000
    logger.info(
        "ElevenLabs TTS done id=%s latency=%.0fms -> %s", request_id, latency_ms, output_path,
    )
    return output_path, latency_ms, request_id


__all__ = ["synthesize_elevenlabs_tts"]
