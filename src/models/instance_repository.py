"""Repository for :class:`ModelInstance`.

Owns CRUD + Fernet encryption of credentials + the "single default per type"
invariant. Callers never touch the DB row class — they pass / receive the
plain :class:`ModelInstance` dataclass (credentials decrypted in memory).

Design notes
============
- **Repository pattern** keeps SQLAlchemy out of the API / pipeline layers.
- **Encryption boundary**: ``credentials`` are decrypted on read, encrypted
  on write. The encrypted JSON blob lives in ``ModelInstanceRow.encrypted_credentials``.
- **Default invariant**: at most one ``is_default=True`` row per
  ``(user_id, instance_type)``. Enforced atomically inside ``set_default``.
- **User isolation**: every method takes ``user_id`` and filters by it.
  Tests assert that one user cannot see another's instances.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Iterable, List, Optional

from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session

from ..auth import security
from ..auth.models import ModelInstanceRow
from .instance import InstanceType, ModelInstance, deserialize_extra_params

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Helpers — encrypt/decrypt credentials JSON blob
# ─────────────────────────────────────────────────────────────────────────


def _encrypt_credentials(creds: Optional[dict]) -> str:
    if not creds:
        return security.encrypt_secret("{}")
    payload = json.dumps(creds or {}, ensure_ascii=False)
    return security.encrypt_secret(payload)


def _decrypt_credentials(blob: Optional[str]) -> dict:
    if not blob:
        return {}
    try:
        plain = security.decrypt_secret(blob)
    except Exception:  # pragma: no cover — only fires on master-key mismatch
        logger.warning("failed to decrypt instance credentials; returning empty dict")
        return {}
    if not plain:
        return {}
    try:
        parsed = json.loads(plain)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _row_to_dataclass(row: ModelInstanceRow) -> ModelInstance:
    return ModelInstance(
        id=row.id,
        user_id=row.user_id,
        instance_type=InstanceType.parse(row.instance_type),
        vendor_id=row.vendor_id,
        model_name=row.model_name,
        display_name=row.display_name,
        credentials=_decrypt_credentials(row.encrypted_credentials),
        base_url=row.base_url or "",
        extra_params=deserialize_extra_params(row.extra_params_json),
        is_default=bool(row.is_default),
        created_at=row.created_at.timestamp() if row.created_at else time.time(),
        updated_at=row.updated_at.timestamp() if row.updated_at else time.time(),
    )


# ─────────────────────────────────────────────────────────────────────────
# Repository
# ─────────────────────────────────────────────────────────────────────────


class InstanceRepository:
    """Thin SQLAlchemy wrapper. One repo per request — sessions are short-lived."""

    def __init__(self, session: Session):
        self._session = session

    # — Reads —

    def list_for_user(
        self,
        user_id: int,
        instance_type: Optional[InstanceType] = None,
    ) -> List[ModelInstance]:
        stmt = select(ModelInstanceRow).where(ModelInstanceRow.user_id == user_id)
        if instance_type is not None:
            stmt = stmt.where(ModelInstanceRow.instance_type == instance_type.value)
        stmt = stmt.order_by(
            ModelInstanceRow.instance_type,
            ModelInstanceRow.is_default.desc(),
            ModelInstanceRow.created_at,
        )
        rows = self._session.execute(stmt).scalars().all()
        return [_row_to_dataclass(r) for r in rows]

    def get(self, instance_id: str, user_id: int) -> Optional[ModelInstance]:
        row = self._session.get(ModelInstanceRow, instance_id)
        if row is None or row.user_id != user_id:
            return None
        return _row_to_dataclass(row)

    def get_default(
        self, user_id: int, instance_type: InstanceType
    ) -> Optional[ModelInstance]:
        stmt = select(ModelInstanceRow).where(
            and_(
                ModelInstanceRow.user_id == user_id,
                ModelInstanceRow.instance_type == instance_type.value,
                ModelInstanceRow.is_default.is_(True),
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return _row_to_dataclass(row) if row else None

    # — Writes —

    def create(self, instance: ModelInstance) -> ModelInstance:
        if not instance.id:
            instance.id = ModelInstance.new_id()
        if not instance.user_id:
            raise ValueError("user_id is required")
        if not instance.display_name:
            raise ValueError("display_name is required")
        if not instance.vendor_id:
            raise ValueError("vendor_id is required")
        if not instance.model_name:
            raise ValueError("model_name is required")

        # If marked default, demote any other default first.
        if instance.is_default:
            self._clear_default(instance.user_id, instance.instance_type)

        row = ModelInstanceRow(
            id=instance.id,
            user_id=instance.user_id,
            instance_type=instance.instance_type.value,
            vendor_id=instance.vendor_id,
            model_name=instance.model_name,
            display_name=instance.display_name,
            encrypted_credentials=_encrypt_credentials(instance.credentials),
            base_url=instance.base_url or "",
            extra_params_json=instance.serialize_extra_params(),
            is_default=instance.is_default,
        )
        self._session.add(row)
        self._session.flush()
        return _row_to_dataclass(row)

    def update(
        self,
        instance_id: str,
        user_id: int,
        *,
        display_name: Optional[str] = None,
        model_name: Optional[str] = None,
        credentials: Optional[dict] = None,
        base_url: Optional[str] = None,
        extra_params: Optional[dict] = None,
    ) -> Optional[ModelInstance]:
        row = self._session.get(ModelInstanceRow, instance_id)
        if row is None or row.user_id != user_id:
            return None
        if display_name is not None:
            row.display_name = display_name
        if model_name is not None:
            row.model_name = model_name
        if credentials is not None:
            row.encrypted_credentials = _encrypt_credentials(credentials)
        if base_url is not None:
            row.base_url = base_url
        if extra_params is not None:
            row.extra_params_json = json.dumps(extra_params, ensure_ascii=False)
        self._session.flush()
        return _row_to_dataclass(row)

    def set_default(
        self, instance_id: str, user_id: int
    ) -> Optional[ModelInstance]:
        row = self._session.get(ModelInstanceRow, instance_id)
        if row is None or row.user_id != user_id:
            return None
        instance_type = InstanceType.parse(row.instance_type)
        self._clear_default(user_id, instance_type)
        row.is_default = True
        self._session.flush()
        return _row_to_dataclass(row)

    def delete(self, instance_id: str, user_id: int) -> bool:
        row = self._session.get(ModelInstanceRow, instance_id)
        if row is None or row.user_id != user_id:
            return False
        self._session.delete(row)
        self._session.flush()
        return True

    # — Private —

    def _clear_default(self, user_id: int, instance_type: InstanceType) -> None:
        stmt = (
            update(ModelInstanceRow)
            .where(
                ModelInstanceRow.user_id == user_id,
                ModelInstanceRow.instance_type == instance_type.value,
                ModelInstanceRow.is_default.is_(True),
            )
            .values(is_default=False)
        )
        self._session.execute(stmt)


__all__ = ["InstanceRepository"]
