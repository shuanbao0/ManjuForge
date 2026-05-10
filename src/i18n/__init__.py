"""Backend i18n.

Pattern mirrors the frontend (`frontend/src/i18n/`):
  - dot-path keys, `{var}` interpolation
  - default locale is zh-CN; en-US falls through to zh-CN for missing keys
  - locale is resolved from the request's Accept-Language header

Usage in route handlers:
    from fastapi import Depends
    from src.i18n import Locale, get_locale, t

    @app.post("/foo")
    def foo(locale: Locale = Depends(get_locale)):
        if bad:
            raise HTTPException(400, detail=t("errors.invalid", locale))

In service-layer code that doesn't see the request, accept a `locale` arg or
let the route translate the message before raising. Keep service-layer raises
in English so they're greppable; translate at the API boundary.
"""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Any, Iterator

from fastapi import Header

from .locales.en_us import messages as _en_us
from .locales.zh_cn import messages as _zh_cn

Locale = str  # "zh-CN" | "en-US"

DEFAULT_LOCALE: Locale = "zh-CN"
SUPPORTED: tuple[Locale, ...] = ("zh-CN", "en-US")

_BUNDLES: dict[Locale, dict[str, Any]] = {
    "zh-CN": _zh_cn,
    "en-US": _en_us,
}

# Per-request locale carried through contextvars so service-layer code (which
# doesn't see the FastAPI request) can pick the right bundle without threading
# the locale through every function signature. Set by the FastAPI middleware
# below; falls back to DEFAULT_LOCALE when unset (CLI / tests / outside-request).
_current_locale: contextvars.ContextVar[Locale] = contextvars.ContextVar(
    "manjuforge_current_locale", default=DEFAULT_LOCALE
)


def get_current_locale() -> Locale:
    return _current_locale.get()


@contextmanager
def use_locale(locale: Locale) -> Iterator[Locale]:
    """Bind ``locale`` to the current call for the duration of the with-block."""
    loc = locale if locale in SUPPORTED else DEFAULT_LOCALE
    token = _current_locale.set(loc)
    try:
        yield loc
    finally:
        _current_locale.reset(token)


def _lookup(bundle: dict[str, Any], key: str) -> str | None:
    cur: Any = bundle
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur if isinstance(cur, str) else None


def _interpolate(template: str, vars: dict[str, Any]) -> str:
    if not vars:
        return template
    out = template
    for k, v in vars.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def t(key: str, locale: Locale | None = None, **vars: Any) -> str:
    """Translate `key` for `locale`, with fallback to zh-CN, then key itself.

    When ``locale`` is omitted, the per-request value bound by ``use_locale``
    (or set automatically by ``LocaleMiddleware``) is used. Outside a request
    the fallback is :data:`DEFAULT_LOCALE`.
    """
    loc_in = locale if locale is not None else _current_locale.get()
    loc = loc_in if loc_in in SUPPORTED else DEFAULT_LOCALE
    primary = _lookup(_BUNDLES[loc], key)
    if primary is not None:
        return _interpolate(primary, vars)
    fallback = _lookup(_BUNDLES[DEFAULT_LOCALE], key)
    if fallback is not None:
        return _interpolate(fallback, vars)
    return key


def parse_accept_language(header_value: str | None) -> Locale:
    """Pick the best matching supported locale from an Accept-Language header.

    Tolerant parser — handles common shapes:
      "en-US,en;q=0.9"  → "en-US"
      "zh-CN"           → "zh-CN"
      "fr"              → DEFAULT_LOCALE (no match)
      None / ""         → DEFAULT_LOCALE
    """
    if not header_value:
        return DEFAULT_LOCALE
    # Order by q-factor (default 1.0). Stable sort keeps original order on ties.
    parts: list[tuple[float, str]] = []
    for chunk in header_value.split(","):
        tag = chunk.strip()
        q = 1.0
        if ";" in tag:
            tag, *params = tag.split(";")
            tag = tag.strip()
            for p in params:
                p = p.strip()
                if p.startswith("q="):
                    try:
                        q = float(p[2:])
                    except ValueError:
                        pass
        if tag:
            parts.append((q, tag))
    parts.sort(key=lambda x: -x[0])
    for _, tag in parts:
        # Exact match first
        if tag in SUPPORTED:
            return tag
        # Language-only match (e.g. "en" → "en-US", "zh" → "zh-CN")
        prefix = tag.split("-")[0].lower()
        for s in SUPPORTED:
            if s.split("-")[0].lower() == prefix:
                return s
    return DEFAULT_LOCALE


def get_locale(accept_language: str | None = Header(default=None)) -> Locale:
    """FastAPI dependency: pick the best supported locale from the request."""
    return parse_accept_language(accept_language)


__all__ = [
    "DEFAULT_LOCALE",
    "Locale",
    "SUPPORTED",
    "get_locale",
    "parse_accept_language",
    "t",
]
