"""Model instance — user-owned, vendor-bound, credential-bearing.

Each ``ModelInstance`` is a fully-configured pointer to one usable model.
It pairs:
- a system-known **vendor** (DashScope / OpenAI / Anthropic / Kling / ...),
- a **model name** the vendor recognises (e.g. ``gpt-5``, ``wan2.6-i2v``),
- the user's **credentials** to reach that vendor,
- a **display name** the user picked,
- optional **base_url** override and per-request **extra_params** defaults.

Projects reference instances by id, so swapping the LLM (or T2I, I2V, ...)
on a project boils down to writing a new instance id into ``ModelSettings``.
The runtime context (see :func:`src.runtime.with_instance`) injects the
instance into the active request, and credential lookups (:func:`get_cred`)
resolve against the instance first.
"""
from __future__ import annotations

import enum
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class InstanceType(str, enum.Enum):
    LLM = "llm"
    T2I = "t2i"
    I2I = "i2i"
    I2V = "i2v"
    T2V = "t2v"
    R2V = "r2v"
    TTS = "tts"

    @classmethod
    def parse(cls, raw: str) -> "InstanceType":
        normalized = (raw or "").strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"unknown instance type: {raw!r}")


@dataclass
class ModelInstance:
    """In-memory shape of one configured model.

    DB row representation lives at :class:`src.auth.models.ModelInstanceRow`.
    Credentials here are **already decrypted** — never serialize this object
    to logs or to network responses without first scrubbing them.
    """

    id: str
    user_id: int
    instance_type: InstanceType
    vendor_id: str
    model_name: str
    display_name: str
    credentials: Dict[str, str] = field(default_factory=dict)
    base_url: str = ""
    extra_params: Dict[str, Any] = field(default_factory=dict)
    is_default: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    def to_public_dict(self) -> Dict[str, Any]:
        """Wire-safe representation: credentials replaced by a presence map.

        Used by GET /me/instances responses so the FE can show "已配置 ✓"
        without ever shipping the secret over the wire.
        """
        return {
            "id": self.id,
            "instance_type": self.instance_type.value,
            "vendor_id": self.vendor_id,
            "model_name": self.model_name,
            "display_name": self.display_name,
            "credential_keys": sorted(k for k, v in self.credentials.items() if v),
            "base_url": self.base_url,
            "extra_params": self.extra_params,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def serialize_extra_params(self) -> str:
        return json.dumps(self.extra_params or {}, ensure_ascii=False)


def deserialize_extra_params(blob: Optional[str]) -> Dict[str, Any]:
    if not blob:
        return {}
    try:
        parsed = json.loads(blob)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


__all__ = ["InstanceType", "ModelInstance", "deserialize_extra_params"]
