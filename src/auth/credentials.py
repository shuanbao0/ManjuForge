"""Per-user encrypted credentials.

Each user has their own DASHSCOPE / Kling / Vidu / OSS / OpenAI keys. They
are stored Fernet-encrypted in the ``user_credentials`` table and surfaced
to providers at request time via :mod:`src.runtime`.

Some keys are admin-controlled and apply instance-wide (``API_HOST``,
``API_PORT``, ``LLM_PROVIDER`` provider lists) — those still live in the
process environment / instance config and are not duplicated here.
"""

from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import security
from .models import User, UserCredential

logger = logging.getLogger(__name__)


# ── Schema ────────────────────────────────────────────────────────────────
#
# Keys we accept. Anything outside this set is rejected on PUT to keep the
# table tidy and to avoid accidental "secret leakage" via free-form keys.

ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        # LLM
        "LLM_PROVIDER",
        "DASHSCOPE_API_KEY",
        "DASHSCOPE_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_MODEL",
        # Provider-direct AKs
        "KLING_PROVIDER_MODE",
        "KLING_ACCESS_KEY",
        "KLING_SECRET_KEY",
        "KLING_BASE_URL",
        "VIDU_PROVIDER_MODE",
        "VIDU_API_KEY",
        "VIDU_BASE_URL",
        "PIXVERSE_PROVIDER_MODE",
        "PIXVERSE_API_KEY",
        "PIXVERSE_BASE_URL",
        # ByteDance Doubao Seedance (vendor-direct only).
        "DOUBAO_PROVIDER_MODE",
        "DOUBAO_API_KEY",
        "DOUBAO_BASE_URL",
        # MiniMax Hailuo 海螺 (vendor-direct only).
        "HAILUO_PROVIDER_MODE",
        "HAILUO_API_KEY",
        "HAILUO_BASE_URL",
        # Unified MiniMax token-plan key — covers LLM / TTS / T2I / I2V on
        # the same MiniMax account so the user pastes one key per instance.
        "MINIMAX_API_KEY",
        "MINIMAX_BASE_URL",
        # Object storage (P4) — provider-agnostic S3 fields
        "STORAGE_PROVIDER",       # minio | aliyun_oss | local_only
        "STORAGE_ENDPOINT",
        "STORAGE_REGION",
        "STORAGE_ACCESS_KEY",
        "STORAGE_SECRET_KEY",
        "STORAGE_BUCKET",
        "STORAGE_PATH_PREFIX",
        # Legacy Aliyun OSS fields (kept readable so existing OSSImageUploader
        # path keeps working until P4 migration is complete in caller code).
        "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
        "OSS_ENDPOINT",
        "OSS_BUCKET_NAME",
        "OSS_BASE_PATH",
    }
)

# Keys whose values are secret (shown masked in GET responses).
SECRET_KEYS: frozenset[str] = frozenset(
    {
        "DASHSCOPE_API_KEY",
        "OPENAI_API_KEY",
        "KLING_ACCESS_KEY",
        "KLING_SECRET_KEY",
        "VIDU_API_KEY",
        "PIXVERSE_API_KEY",
        "DOUBAO_API_KEY",
        "HAILUO_API_KEY",
        "MINIMAX_API_KEY",
        "STORAGE_ACCESS_KEY",
        "STORAGE_SECRET_KEY",
        "ALIBABA_CLOUD_ACCESS_KEY_ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
    }
)


# ── DB I/O ────────────────────────────────────────────────────────────────


def load_for_user(session: Session, user_id: int) -> dict[str, str]:
    """Decrypt and return all credentials for *user_id* as a plain dict."""
    rows = session.scalars(
        select(UserCredential).where(UserCredential.user_id == user_id)
    ).all()
    out: dict[str, str] = {}
    for row in rows:
        if row.key not in ALLOWED_KEYS:
            continue
        out[row.key] = security.decrypt_secret(row.value_encrypted)
    return out


def replace_for_user(session: Session, user_id: int, values: dict[str, str]) -> dict[str, str]:
    """Atomic full replace: anything not in *values* is removed; anything in
    *values* is upserted with encrypted value. Returns the resulting dict."""
    rows = session.scalars(
        select(UserCredential).where(UserCredential.user_id == user_id)
    ).all()
    by_key = {row.key: row for row in rows}

    cleaned: dict[str, str] = {}
    for key, value in values.items():
        if key not in ALLOWED_KEYS:
            logger.warning("replace_for_user: ignoring unknown key %s for user %s", key, user_id)
            continue
        cleaned[key] = (value or "").strip()

    # Upsert each provided key; delete keys that weren't sent (treat absent as cleared).
    for key, value in cleaned.items():
        encrypted = security.encrypt_secret(value)
        row = by_key.pop(key, None)
        if row is None:
            session.add(UserCredential(user_id=user_id, key=key, value_encrypted=encrypted))
        else:
            row.value_encrypted = encrypted

    for stale in by_key.values():
        session.delete(stale)

    session.flush()
    return cleaned


def patch_for_user(session: Session, user_id: int, patch: dict[str, str]) -> dict[str, str]:
    """Partial update: only keys present in *patch* are touched. Empty
    string clears the value (keeps the row but sets it empty)."""
    rows = session.scalars(
        select(UserCredential).where(
            UserCredential.user_id == user_id,
            UserCredential.key.in_(list(patch.keys())),
        )
    ).all()
    by_key = {row.key: row for row in rows}

    for key, value in patch.items():
        if key not in ALLOWED_KEYS:
            logger.warning("patch_for_user: ignoring unknown key %s for user %s", key, user_id)
            continue
        encrypted = security.encrypt_secret((value or "").strip())
        row = by_key.get(key)
        if row is None:
            session.add(UserCredential(user_id=user_id, key=key, value_encrypted=encrypted))
        else:
            row.value_encrypted = encrypted

    session.flush()
    return load_for_user(session, user_id)


def delete_keys(session: Session, user_id: int, keys: Iterable[str]) -> None:
    rows = session.scalars(
        select(UserCredential).where(
            UserCredential.user_id == user_id,
            UserCredential.key.in_(list(keys)),
        )
    ).all()
    for row in rows:
        session.delete(row)
    session.flush()


# ── Masking for display ───────────────────────────────────────────────────


def mask_value(key: str, value: str) -> str:
    if not value:
        return ""
    if key not in SECRET_KEYS:
        return value
    if len(value) <= 4:
        return "•" * len(value)
    return value[:2] + "•" * (len(value) - 6) + value[-4:]


def project_for_display(creds: dict[str, str]) -> dict[str, str]:
    """Return a copy where secret values are masked for safe UI rendering."""
    return {key: mask_value(key, val) for key, val in creds.items()}
