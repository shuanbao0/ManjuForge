"""Per-request runtime context.

In a multi-user single-instance deployment we need three pieces of state to
follow each HTTP request through the codebase without having to thread them
through every function signature:

* the authenticated User (id, role, email)
* that user's resolved credentials (DASHSCOPE_API_KEY etc., decrypted on demand)
* the per-user ComicGenPipeline (with its own ``output/users/<uid>/...`` dir)

We use ``contextvars`` because Starlette / FastAPI propagates them across
async boundaries within a single request, and they keep concurrent requests
properly isolated.

When code runs *outside* a request (CLI scripts, tests, the eager startup
log) the ContextVars are unset; in that case helpers fall back to the
process environment so existing behavior is preserved.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
import os
from typing import Any, Mapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .auth.models import User


@dataclass(frozen=True)
class RequestContext:
    """All per-request state visible to non-route code via :data:`_current`.

    The pipeline lives elsewhere — see
    :func:`src.apps.comic_gen.pipeline_factory.current_pipeline` — because
    its lookup is a ``user_id → ComicGenPipeline`` map that can be primed
    lazily and shared across threads. RequestContext carries only the
    user and decrypted credentials.
    """

    user: "User"
    creds: Mapping[str, str]


_current: ContextVar[Optional[RequestContext]] = ContextVar(
    "manjuforge_request_context", default=None
)


def set_context(ctx: RequestContext) -> Token:
    return _current.set(ctx)


def reset_context(token: Token) -> None:
    _current.reset(token)


def get_context() -> Optional[RequestContext]:
    return _current.get()


def current_user() -> Optional["User"]:
    ctx = _current.get()
    return ctx.user if ctx else None


def current_user_id() -> Optional[int]:
    u = current_user()
    return u.id if u is not None else None


def get_cred(key: str, default: str = "") -> str:
    """Return the named credential for the current request's user.

    **Resolution order**:

    1. Per-user credentials saved via ``PUT /me/credentials`` (decrypted on
       every request by the auth middleware).
    2. Process environment / ``.env`` — used as a tenant-wide *fallback*
       so an operator can pre-seed defaults (DashScope key, OSS bucket)
       without forcing every user to fill the same value.

    Outside an HTTP request (tests, startup, CLI) only step 2 applies.
    Returns ``""`` when neither layer has the key — same shape as
    ``os.getenv(name, "")`` so existing callers don't need null checks.
    """
    ctx = _current.get()
    if ctx is not None:
        v = ctx.creds.get(key)
        if v:  # treat empty string as "not configured" — fall through to env
            return v
    return os.getenv(key, default) or default


def has_cred(key: str) -> bool:
    return bool(get_cred(key))


def cred_snapshot() -> dict[str, str]:
    """Returns a copy of the current request's credentials, or {} outside a request."""
    ctx = _current.get()
    return dict(ctx.creds) if ctx else {}


# ── Async-safe execution helpers ──────────────────────────────────────────
#
# ContextVars do *not* propagate across thread boundaries. Anything that
# offloads work to a ThreadPoolExecutor (``loop.run_in_executor``) or to a
# sync FastAPI ``BackgroundTask`` will see an empty RequestContext unless
# we explicitly carry it across. These helpers do that carry; route code
# should prefer them over the raw asyncio / Starlette primitives.
#
# Without this, all per-user credentials silently fall back to the process
# environment for any blocking call (LLM analysis, generation, OSS upload).


import asyncio
import contextvars
import functools
from typing import Any, Awaitable, Callable, Optional


def run_in_executor(
    loop: Optional[asyncio.AbstractEventLoop],
    fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Awaitable[Any]:
    """Like ``loop.run_in_executor(None, partial(fn, *args, **kwargs))`` but
    propagates the current request's :class:`RequestContext` into the worker
    thread, so per-user credentials remain visible to provider clients.
    """
    loop = loop or asyncio.get_event_loop()
    ctx = contextvars.copy_context()

    def _runner() -> Any:
        return ctx.run(fn, *args, **kwargs)

    return loop.run_in_executor(None, _runner)


def add_background_task(background_tasks, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """Wrap ``BackgroundTasks.add_task`` so the callback runs inside a
    snapshot of the current request context.

    Works for both sync and async callbacks. For sync callbacks Starlette
    will dispatch to the threadpool, where ContextVars would otherwise be
    lost; we wrap with ``ctx.run`` to carry them.
    """
    ctx = contextvars.copy_context()

    if asyncio.iscoroutinefunction(fn):
        # Async tasks already share the loop's task tree; just bind args.
        async def _async_wrapper() -> None:
            await ctx.run(asyncio.ensure_future, fn(*args, **kwargs))  # type: ignore[arg-type]

        # Simpler & correct: schedule directly with bound args; ContextVars
        # propagate inside the same event-loop task.
        background_tasks.add_task(fn, *args, **kwargs)
        return

    @functools.wraps(fn)
    def _sync_wrapper(*a: Any, **kw: Any) -> Any:
        return ctx.run(fn, *a, **kw)

    background_tasks.add_task(_sync_wrapper, *args, **kwargs)


__all__ = [
    "RequestContext",
    "set_context",
    "reset_context",
    "get_context",
    "current_user",
    "current_user_id",
    "get_cred",
    "has_cred",
    "cred_snapshot",
    "run_in_executor",
    "add_background_task",
]
