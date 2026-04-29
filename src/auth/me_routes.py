"""Per-user resource routes: ``/me/credentials``, ``/me/files`` (P4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import credentials as creds_store
from .deps import get_current_user, get_db
from .models import User

router = APIRouter(prefix="/me", tags=["me"])


def _evict_storage_caches(user_id: int) -> None:
    """Drop any cached storage clients holding stale keys for this user.

    Called whenever the user's credentials change. Without this, a freshly
    PUT-ed key would still see the old ``OSSImageUploader`` / ``S3Client``
    until process restart because they cache by user_id.
    """
    try:
        from ..utils.oss_utils import OSSImageUploader  # noqa: WPS433  local to break cycle
        OSSImageUploader.reset_instance(user_id)
    except Exception:  # pragma: no cover
        pass
    try:
        from ..utils.object_storage import ObjectStorageClient  # noqa: WPS433
        ObjectStorageClient.reset_cache(user_id)
    except Exception:  # pragma: no cover
        pass


class CredentialsOut(BaseModel):
    """Returned to the client. Secrets are masked unless ``reveal=true``."""

    values: dict[str, str] = Field(default_factory=dict)
    masked: bool = True


class CredentialsReplace(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class CredentialsPatch(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


@router.get("/credentials", response_model=CredentialsOut)
def get_my_credentials(
    reveal: bool = Query(False, description="If true, return raw secret values instead of masked. Use with care."),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CredentialsOut:
    raw = creds_store.load_for_user(db, user.id)
    if reveal:
        return CredentialsOut(values=raw, masked=False)
    return CredentialsOut(values=creds_store.project_for_display(raw), masked=True)


@router.put("/credentials", response_model=CredentialsOut)
def replace_my_credentials(
    payload: CredentialsReplace,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CredentialsOut:
    saved = creds_store.replace_for_user(db, user.id, payload.values)
    _evict_storage_caches(user.id)
    return CredentialsOut(values=creds_store.project_for_display(saved), masked=True)


@router.patch("/credentials", response_model=CredentialsOut)
def patch_my_credentials(
    payload: CredentialsPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CredentialsOut:
    saved = creds_store.patch_for_user(db, user.id, payload.values)
    _evict_storage_caches(user.id)
    return CredentialsOut(values=creds_store.project_for_display(saved), masked=True)


@router.delete("/credentials/{key}", status_code=204)
def delete_my_credential(
    key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    if key not in creds_store.ALLOWED_KEYS:
        raise HTTPException(status_code=400, detail={"code": "UNKNOWN_KEY", "message": f"unknown credential key: {key}"})
    creds_store.delete_keys(db, user.id, [key])
    _evict_storage_caches(user.id)
    return None


@router.get("/credentials/keys", response_model=list[str])
def list_credential_keys(
    user: User = Depends(get_current_user),  # noqa: ARG001
) -> list[str]:
    """List of credential keys this server accepts (for UI driving)."""
    return sorted(creds_store.ALLOWED_KEYS)
