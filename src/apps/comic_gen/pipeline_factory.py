"""Per-user :class:`ComicGenPipeline` cache and a transparent proxy.

The legacy code path uses a single module-level ``pipeline`` object. With
multi-user data isolation we still want that ergonomic singleton from the
caller's point of view — but each request must get a pipeline scoped to
the current user's ``output/users/<uid>/`` directory.

We give callers a proxy object that forwards every attribute access to
the per-request pipeline resolved from :func:`runtime.current_user_id`.
There's also a ``legacy_global_pipeline`` for code paths that fire
*outside* a request (the eager startup log, scripts, tests). It points
at the original ``output/`` root, exactly matching the behavior before
the multi-tenant refactor.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Optional

from ... import runtime
from ...auth.models import User  # noqa: F401  (kept for type ergonomics)
from .pipeline import ComicGenPipeline

logger = logging.getLogger(__name__)


_PER_USER_LOCK = threading.RLock()
_PER_USER_CACHE: dict[int, ComicGenPipeline] = {}

# Single-tenant fallback: same behavior the project had before P2.
_LEGACY_LOCK = threading.RLock()
_legacy: Optional[ComicGenPipeline] = None


def _user_data_root(user_id: int) -> str:
    return os.path.join("output", "users", str(user_id))


def get_pipeline_for_user(user_id: int) -> ComicGenPipeline:
    with _PER_USER_LOCK:
        existing = _PER_USER_CACHE.get(user_id)
        if existing is not None:
            return existing
        root = _user_data_root(user_id)
        os.makedirs(root, exist_ok=True)
        pipeline = ComicGenPipeline(data_root=root)
        _PER_USER_CACHE[user_id] = pipeline
        logger.info("Created pipeline for user %s with data_root=%s", user_id, root)
        return pipeline


def evict_user(user_id: int) -> None:
    with _PER_USER_LOCK:
        _PER_USER_CACHE.pop(user_id, None)


def legacy_global_pipeline() -> ComicGenPipeline:
    """Single-tenant fallback used when no request user is available."""
    global _legacy
    with _LEGACY_LOCK:
        if _legacy is None:
            os.makedirs("output", exist_ok=True)
            _legacy = ComicGenPipeline(data_root="output")
        return _legacy


def current_pipeline() -> ComicGenPipeline:
    """Resolve the right pipeline for the calling context.

    * Inside a request → per-user pipeline (created on first hit).
    * Outside a request (startup, CLI, tests) → legacy single-tenant.
    """
    user = runtime.current_user()
    if user is None:
        return legacy_global_pipeline()
    return get_pipeline_for_user(user.id)


class _PipelineProxy:
    """Forwards attribute access to :func:`current_pipeline` lazily.

    Existing routes write things like ``pipeline.create_script(...)`` —
    those keep compiling unchanged but now hit the right per-user
    pipeline depending on who's authenticated.
    """

    __slots__ = ()

    def __getattr__(self, item: str) -> Any:
        # Avoid infinite recursion on dunder lookups by routing all reads
        # through the resolver.
        return getattr(current_pipeline(), item)

    def __setattr__(self, key: str, value: Any) -> None:
        setattr(current_pipeline(), key, value)

    def __repr__(self) -> str:  # pragma: no cover - debug-only
        return f"<PipelineProxy {current_pipeline()!r}>"


pipeline_proxy: ComicGenPipeline = _PipelineProxy()  # type: ignore[assignment]
