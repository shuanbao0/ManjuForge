"""Auth-facing HTTP routes: setup, login, me, password change."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import schemas, service
from .deps import get_current_user, get_db
from .models import User

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.get("/setup-status", response_model=schemas.SetupStatus)
def setup_status_route(db: Session = Depends(get_db)) -> schemas.SetupStatus:
    return service.setup_status(db)


@router.post("/setup", response_model=schemas.TokenOut, status_code=201)
def setup_route(
    payload: schemas.SetupRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.TokenOut:
    try:
        user = service.bootstrap_admin(db, payload)
    except service.AuthError as e:
        raise _to_http(e) from e

    token, expires_at = service.issue_token(user)
    service.record_audit(
        db, action="auth.setup", actor=user, target=user, ip=_client_ip(request),
    )
    return schemas.TokenOut(
        access_token=token,
        expires_at=expires_at,
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/login", response_model=schemas.TokenOut)
def login_route(
    payload: schemas.LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.TokenOut:
    try:
        user, token, expires_at = service.login(db, payload)
    except service.AuthError as e:
        # Best-effort failure audit; don't leak which step failed.
        service.record_audit(
            db, action="auth.login.failed",
            detail=f"email={payload.email[:255]};code={e.code}",
            ip=_client_ip(request),
        )
        raise _to_http(e) from e

    service.record_audit(
        db, action="auth.login", actor=user, target=user, ip=_client_ip(request),
    )
    return schemas.TokenOut(
        access_token=token,
        expires_at=expires_at,
        user=schemas.UserOut.model_validate(user),
    )


@router.get("/me", response_model=schemas.UserOut)
def me_route(user: User = Depends(get_current_user)) -> schemas.UserOut:
    return schemas.UserOut.model_validate(user)


@router.post("/password", response_model=schemas.TokenOut)
def change_password_route(
    payload: schemas.ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> schemas.TokenOut:
    try:
        service.change_password(db, user, payload.current_password, payload.new_password)
    except service.AuthError as e:
        raise _to_http(e) from e

    token, expires_at = service.issue_token(user)
    service.record_audit(
        db, action="auth.password.change", actor=user, target=user, ip=_client_ip(request),
    )
    return schemas.TokenOut(
        access_token=token,
        expires_at=expires_at,
        user=schemas.UserOut.model_validate(user),
    )


@router.post("/logout", status_code=204)
def logout_route(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Invalidate all of this user's outstanding tokens by bumping token_version."""
    user.token_version += 1
    db.flush()
    service.record_audit(
        db, action="auth.logout", actor=user, target=user, ip=_client_ip(request),
    )
    return None
