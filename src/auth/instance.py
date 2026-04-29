"""Instance-level secrets bootstrap.

Generates and persists per-installation secrets that must remain stable
across restarts (JWT signing key, Fernet master key for credential
encryption). They live in `~/.manjuforge/instance.json` regardless of
dev / packaged mode — these are infrastructure secrets, not user data,
and should never appear in `.env`.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import threading
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet


_INSTANCE_FILE = "instance.json"
_lock = threading.Lock()


def _instance_path() -> Path:
    from .. import utils  # local import to avoid cycles at module load

    base = Path(utils.get_user_data_dir())
    base.mkdir(parents=True, exist_ok=True)
    return base / _INSTANCE_FILE


def _load() -> dict:
    path = _instance_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    path = _instance_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _generate_jwt_secret() -> str:
    return secrets.token_urlsafe(48)


def _generate_master_key() -> str:
    # Fernet key must be 32 url-safe base64 bytes
    return Fernet.generate_key().decode("ascii")


def ensure_instance_secrets() -> dict:
    """Read secrets from disk, generating any that are missing.

    Returns the resolved {jwt_secret, master_key, instance_id} dict.
    Idempotent and safe to call from multiple threads.
    """
    with _lock:
        data = _load()
        changed = False

        # Allow override via env so containers / tests can pin values.
        jwt_secret = os.getenv("MANJU_FORGE_JWT_SECRET") or data.get("jwt_secret")
        if not jwt_secret:
            jwt_secret = _generate_jwt_secret()
            data["jwt_secret"] = jwt_secret
            changed = True
        else:
            data["jwt_secret"] = jwt_secret

        master_key = os.getenv("MANJU_FORGE_MASTER_KEY") or data.get("master_key")
        if not master_key:
            master_key = _generate_master_key()
            data["master_key"] = master_key
            changed = True
        else:
            data["master_key"] = master_key

        instance_id = data.get("instance_id")
        if not instance_id:
            instance_id = base64.urlsafe_b64encode(secrets.token_bytes(12)).decode("ascii").rstrip("=")
            data["instance_id"] = instance_id
            changed = True

        if changed:
            _save(data)
        return data


def get_jwt_secret() -> str:
    return ensure_instance_secrets()["jwt_secret"]


def get_master_key() -> str:
    return ensure_instance_secrets()["master_key"]


def get_instance_id() -> str:
    return ensure_instance_secrets()["instance_id"]


def get_db_path() -> str:
    """Path to the auth/users SQLite database. Co-located with instance secrets."""
    override: Optional[str] = os.getenv("MANJU_FORGE_DB_PATH")
    if override:
        Path(override).parent.mkdir(parents=True, exist_ok=True)
        return override
    return str(_instance_path().parent / "manjuforge.db")
