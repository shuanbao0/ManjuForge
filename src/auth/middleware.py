"""Starlette middleware that authenticates every incoming request and
populates the per-request ``runtime.RequestContext``.

Why a middleware instead of a per-route ``Depends``?

* There are 85+ existing business routes in ``src/apps/comic_gen/api.py``.
  Adding a dependency to every signature would be invasive *and* would not
  cover code paths reached via ``app.mount()`` or background tasks that
  read credentials.
* ContextVars survive across ``await`` boundaries within a single request,
  so model clients written today as plain sync functions can keep using
  ``runtime.get_cred("...")`` without becoming async.
"""

from __future__ import annotations

import json
import logging
from typing import Awaitable, Callable, Iterable

from fastapi import status
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src import runtime
from . import credentials as creds_store, service
from .db import get_session_factory
from .security import (
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    decode_access_token,
)

logger = logging.getLogger(__name__)


def _is_prefix_match(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in prefixes)


# Routes that *must* be reachable without auth. Login flows, swagger, the
# bootstrap-status check the SetupGate uses, and a couple of platform
# probes (favicon, redoc).
PUBLIC_PATHS: tuple[str, ...] = (
    "/auth/setup-status",
    "/auth/setup",
    "/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)

# Path prefixes whose routes already enforce auth via FastAPI Depends —
# we let them through here so they can produce their own 401 / 403 with
# the right error code shape that callers expect.
#
# NOTE: ``/me/files/{path}`` is intentionally *not* in this set. It's a
# file-serving endpoint that needs the middleware to (a) populate the
# request context (so per-user storage clients work) and (b) enforce auth
# uniformly with ``/files/*``. Only the credential-CRUD ``/me/...`` routes
# are Depends-handled.
HANDLED_BY_DEPENDS: tuple[str, ...] = (
    "/auth/",
    "/admin/",
    "/me/credentials",
)


def _unauthorized(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": {"code": code, "message": message}},
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthContextMiddleware(BaseHTTPMiddleware):
    """Authenticates business-API requests and attaches RequestContext."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path

        # Public paths and Depends-handled prefixes pass straight through.
        # /auth/* needs the DB session for Depends to work, and we don't
        # want to pre-validate (it would 401 before the dependency had a
        # chance to handle bootstrap / login flows).
        if _is_prefix_match(path, PUBLIC_PATHS) or _is_prefix_match(path, HANDLED_BY_DEPENDS):
            return await call_next(request)

        # CORS preflight — Starlette handles this before us, but be defensive.
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract bearer token.
        authz = request.headers.get("authorization", "")
        if not authz.lower().startswith("bearer "):
            return _unauthorized("UNAUTHORIZED", "authorization header is required")
        token = authz.split(" ", 1)[1].strip()
        if not token:
            return _unauthorized("UNAUTHORIZED", "authorization header is required")

        try:
            claims = decode_access_token(token)
        except TokenExpiredError:
            return _unauthorized("TOKEN_EXPIRED", "token has expired")
        except TokenInvalidError:
            return _unauthorized("INVALID_TOKEN", "invalid token")
        except TokenError:
            return _unauthorized("INVALID_TOKEN", "invalid token")

        try:
            user_id = int(claims.get("sub", ""))
        except (TypeError, ValueError):
            return _unauthorized("INVALID_TOKEN", "invalid token subject")

        # Resolve user + creds in a short-lived session, then close it.
        # We don't attach this session to request.state — Depends-driven
        # routes get their own.
        factory = get_session_factory()
        session: Session = factory()
        try:
            user = service.get_user(session, user_id)
            if user is None:
                return _unauthorized("USER_NOT_FOUND", "user not found")
            if not user.is_active:
                return _unauthorized("USER_INACTIVE", "user is not active")
            if int(claims.get("tv", -1)) != user.token_version:
                return _unauthorized("TOKEN_REVOKED", "token has been revoked")
            creds = creds_store.load_for_user(session, user_id)
        finally:
            session.close()

        request.state.user = user

        # Pipeline is bound below by the per-user factory dependency. We
        # don't import that here to avoid pulling the comic_gen package at
        # auth-module import time (cyclical risk). The pipeline proxy
        # resolves lazily off ``runtime.current_user_id()``.
        ctx = runtime.RequestContext(user=user, creds=creds)
        token_ctx = runtime.set_context(ctx)
        try:
            return await call_next(request)
        finally:
            runtime.reset_context(token_ctx)
