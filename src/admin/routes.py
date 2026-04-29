"""Admin-only HTTP routes: user management, settings, audit, stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..auth import schemas, service
from ..auth.deps import get_db, require_admin
from ..auth.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


def _to_http(exc: service.AuthError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": str(exc)},
    )


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host[:64]
    return ""


# ── Users ─────────────────────────────────────────────────────────────────


@router.get("/users", response_model=list[schemas.UserOut])
def list_users_route(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[schemas.UserOut]:
    return [schemas.UserOut.model_validate(u) for u in service.list_users(db)]


@router.get("/users/{user_id}", response_model=schemas.UserOut)
def get_user_route(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> schemas.UserOut:
    user = service.get_user(db, user_id)
    if user is None:
        raise _to_http(service.UserNotFound())
    return schemas.UserOut.model_validate(user)


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user_route(
    payload: schemas.CreateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> schemas.UserOut:
    try:
        user = service.admin_create_user(db, payload)
    except service.AuthError as e:
        raise _to_http(e) from e
    service.record_audit(
        db, action="admin.user.create", actor=admin, target=user,
        detail=f"role={user.role}", ip=_client_ip(request),
    )
    return schemas.UserOut.model_validate(user)


@router.patch("/users/{user_id}", response_model=schemas.UserOut)
def update_user_route(
    user_id: int,
    payload: schemas.UpdateUserRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> schemas.UserOut:
    try:
        user = service.admin_update_user(db, user_id, payload)
    except service.AuthError as e:
        raise _to_http(e) from e
    changed = sorted(payload.model_dump(exclude_none=True, exclude={"new_password"}).keys())
    detail = "fields=" + ",".join(changed) if changed else ""
    if payload.new_password:
        detail = (detail + ";password_reset").lstrip(";")
    service.record_audit(
        db, action="admin.user.update", actor=admin, target=user,
        detail=detail, ip=_client_ip(request),
    )
    return schemas.UserOut.model_validate(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user_route(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    target = service.get_user(db, user_id)
    try:
        service.admin_delete_user(db, user_id, requested_by=admin.id)
    except service.AuthError as e:
        raise _to_http(e) from e
    service.record_audit(
        db, action="admin.user.delete", actor=admin, target=target,
        ip=_client_ip(request),
    )
    return None


@router.post("/users/{user_id}/force-logout", response_model=schemas.UserOut)
def force_logout_route(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> schemas.UserOut:
    try:
        user = service.force_logout(db, user_id)
    except service.AuthError as e:
        raise _to_http(e) from e
    service.record_audit(
        db, action="admin.user.force_logout", actor=admin, target=user,
        ip=_client_ip(request),
    )
    return schemas.UserOut.model_validate(user)


# ── Stats ─────────────────────────────────────────────────────────────────


@router.get("/stats", response_model=schemas.AdminStats)
def stats_route(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> schemas.AdminStats:
    return service.admin_stats(db)


# ── Audit log ─────────────────────────────────────────────────────────────


@router.get("/audit-logs", response_model=list[schemas.AuditLogOut])
def audit_logs_route(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[schemas.AuditLogOut]:
    return [schemas.AuditLogOut.model_validate(e) for e in service.list_audit_logs(db, limit=limit, offset=offset)]


# ── Settings ──────────────────────────────────────────────────────────────


@router.get("/settings", response_model=schemas.SettingsOut)
def get_settings_route(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> schemas.SettingsOut:
    return service.get_settings(db)


@router.put("/settings", response_model=schemas.SettingsOut)
def update_settings_route(
    payload: schemas.SettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> schemas.SettingsOut:
    out = service.update_settings(db, payload)
    service.record_audit(
        db, action="admin.settings.update", actor=admin,
        detail=str(payload.model_dump(exclude_none=True)), ip=_client_ip(request),
    )
    return out
