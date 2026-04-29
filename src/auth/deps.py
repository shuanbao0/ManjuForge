"""FastAPI dependency providers for auth: DB session, current user, admin gate."""

from __future__ import annotations

import logging
from typing import Iterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import service
from .db import get_session_factory
from .models import User
from .security import (
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    decode_access_token,
)

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def get_db() -> Iterator[Session]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _unauthorized(detail: str, code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": detail},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise _unauthorized("authorization header is required", "UNAUTHORIZED")

    try:
        claims = decode_access_token(creds.credentials)
    except TokenExpiredError:
        raise _unauthorized("token has expired", "TOKEN_EXPIRED") from None
    except TokenInvalidError:
        raise _unauthorized("invalid token", "INVALID_TOKEN") from None
    except TokenError:
        raise _unauthorized("invalid token", "INVALID_TOKEN") from None

    try:
        user_id = int(claims.get("sub", ""))
    except (TypeError, ValueError):
        raise _unauthorized("invalid token subject", "INVALID_TOKEN") from None

    user = service.get_user(db, user_id)
    if user is None:
        raise _unauthorized("user not found", "USER_NOT_FOUND")
    if not user.is_active:
        raise _unauthorized("user is not active", "USER_INACTIVE")

    if int(claims.get("tv", -1)) != user.token_version:
        raise _unauthorized("token has been revoked", "TOKEN_REVOKED")

    request.state.user = user
    service.touch_active(db, user)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "admin access required"},
        )
    return user
