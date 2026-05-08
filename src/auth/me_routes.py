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


# ── Model instances ──────────────────────────────────────────────────────
#
# Replaces the flat /me/credentials KV store. Every configured model is a
# row owned by the user, with its own credentials, vendor binding, model
# name, and optional default flag. See src/models/instance.py for the
# data model and src/models/instance_repository.py for CRUD semantics.

from ..models.instance import InstanceType, ModelInstance  # noqa: E402
from ..models.instance_repository import InstanceRepository  # noqa: E402


class InstanceCreate(BaseModel):
    instance_type: str
    vendor_id: str
    model_name: str
    display_name: str
    credentials: dict[str, str] = Field(default_factory=dict)
    base_url: str = ""
    extra_params: dict = Field(default_factory=dict)
    is_default: bool = False


class InstanceUpdate(BaseModel):
    display_name: str | None = None
    model_name: str | None = None
    credentials: dict[str, str] | None = None
    base_url: str | None = None
    extra_params: dict | None = None


class InstanceOut(BaseModel):
    """Wire-safe instance shape — credentials replaced by a presence map."""

    id: str
    instance_type: str
    vendor_id: str
    model_name: str
    display_name: str
    credential_keys: list[str]
    base_url: str
    extra_params: dict
    is_default: bool
    created_at: float
    updated_at: float


def _to_out(instance: ModelInstance) -> InstanceOut:
    return InstanceOut(**instance.to_public_dict())


@router.get("/instances", response_model=list[InstanceOut])
def list_my_instances(
    type: str | None = Query(None, description="Filter by instance type"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InstanceOut]:
    repo = InstanceRepository(db)
    type_filter: InstanceType | None = None
    if type:
        try:
            type_filter = InstanceType.parse(type)
        except ValueError:
            raise HTTPException(status_code=400, detail={"code": "BAD_TYPE", "message": f"unknown instance type: {type}"})
    return [_to_out(i) for i in repo.list_for_user(user.id, instance_type=type_filter)]


@router.post("/instances", response_model=InstanceOut, status_code=201)
def create_my_instance(
    payload: InstanceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InstanceOut:
    try:
        itype = InstanceType.parse(payload.instance_type)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "BAD_TYPE", "message": f"unknown instance type: {payload.instance_type}"})
    instance = ModelInstance(
        id=ModelInstance.new_id(),
        user_id=user.id,
        instance_type=itype,
        vendor_id=payload.vendor_id,
        model_name=payload.model_name,
        display_name=payload.display_name,
        credentials=payload.credentials,
        base_url=payload.base_url,
        extra_params=payload.extra_params,
        is_default=payload.is_default,
    )
    repo = InstanceRepository(db)
    try:
        created = repo.create(instance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID", "message": str(e)})
    db.commit()
    return _to_out(created)


@router.get("/instances/{instance_id}", response_model=InstanceOut)
def get_my_instance(
    instance_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InstanceOut:
    repo = InstanceRepository(db)
    instance = repo.get(instance_id, user.id)
    if instance is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "instance not found"})
    return _to_out(instance)


@router.put("/instances/{instance_id}", response_model=InstanceOut)
def update_my_instance(
    instance_id: str,
    payload: InstanceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InstanceOut:
    repo = InstanceRepository(db)
    updated = repo.update(
        instance_id,
        user.id,
        display_name=payload.display_name,
        model_name=payload.model_name,
        credentials=payload.credentials,
        base_url=payload.base_url,
        extra_params=payload.extra_params,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "instance not found"})
    db.commit()
    return _to_out(updated)


@router.delete("/instances/{instance_id}", status_code=204)
def delete_my_instance(
    instance_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    repo = InstanceRepository(db)
    if not repo.delete(instance_id, user.id):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "instance not found"})
    db.commit()


@router.post("/instances/{instance_id}/set-default", response_model=InstanceOut)
def set_my_instance_default(
    instance_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InstanceOut:
    repo = InstanceRepository(db)
    promoted = repo.set_default(instance_id, user.id)
    if promoted is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "instance not found"})
    db.commit()
    return _to_out(promoted)


class InstanceTestResult(BaseModel):
    ok: bool
    latency_ms: float = 0.0
    error: str = ""


@router.post("/instances/{instance_id}/test", response_model=InstanceTestResult)
def test_my_instance(
    instance_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InstanceTestResult:
    """Probe connectivity. Each instance type has its own ping (Strategy
    pattern via ``src/models/instance_testers.py``)."""
    repo = InstanceRepository(db)
    instance = repo.get(instance_id, user.id)
    if instance is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "instance not found"})
    from ..models.instance_testers import test_instance
    result = test_instance(instance)
    return InstanceTestResult(ok=result.ok, latency_ms=result.latency_ms, error=result.error)
