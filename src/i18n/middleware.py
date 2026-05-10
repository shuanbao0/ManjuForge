"""Starlette middleware that binds the request's locale to the i18n contextvar.

Mount once on the FastAPI app; all downstream handlers (and any service-layer
code they call) can then call ``t(key)`` without passing the locale around.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from . import _current_locale, parse_accept_language


class LocaleMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        accept_language = request.headers.get("accept-language")
        locale = parse_accept_language(accept_language)
        token = _current_locale.set(locale)
        try:
            response: Response = await call_next(request)
        finally:
            _current_locale.reset(token)
        # Echo the resolved locale back so frontends can verify what we picked.
        response.headers["Content-Language"] = locale
        return response


__all__ = ["LocaleMiddleware"]
