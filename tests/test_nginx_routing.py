"""Guard the nginx Docker config against missing API route prefixes.

The nginx vhost in ``docker/nginx.conf`` proxies to the FastAPI backend only
for an explicit list of top-level path prefixes. Anything outside that list
falls through to the SPA index.html, which causes opaque "Unexpected token
'<', '<!DOCTYPE'..." JSON-parse errors in the browser.

This test enumerates the actual top-level path prefixes registered on the
FastAPI app and asserts each one is mentioned in the nginx config. It does
not need a real network — pure file inspection.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.apps.comic_gen.api import app


REPO_ROOT = Path(__file__).resolve().parent.parent
NGINX_CONF = REPO_ROOT / "docker" / "nginx.conf"


def _top_level_prefixes() -> set[str]:
    """Collect every distinct first path segment FastAPI exposes."""
    prefixes: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path or not path.startswith("/"):
            continue
        # Drop the leading slash, take the segment up to the next "/" or "{".
        segment = path[1:].split("/", 1)[0].split("{", 1)[0]
        if segment:
            prefixes.add(segment)
    # Auth routes registered under `/auth` and admin under `/admin` come from
    # APIRouter sub-apps; FastAPI exposes them on the same `app.routes` so
    # they are picked up automatically.
    return prefixes


# A handful of segments shouldn't be exposed by nginx (they live behind
# auth/admin or are special). Keep this list tight.
_IGNORED_PREFIXES = {
    "openapi.json",  # explicit exact match in nginx, written without slashes
    "redoc",
    "favicon.ico",
}


def test_nginx_routes_match_fastapi_prefixes():
    if not NGINX_CONF.exists():  # pragma: no cover — Docker config is required
        pytest.skip("docker/nginx.conf not present")

    conf = NGINX_CONF.read_text()

    # Pull the alternation list from the regex location block.
    match = re.search(r"location\s+~\s+\^/\(([^)]+)\)", conf)
    assert match, "nginx.conf must declare a regex location for backend prefixes"

    nginx_prefixes = {p.replace(r"\.", ".") for p in match.group(1).split("|")}

    fastapi_prefixes = _top_level_prefixes() - _IGNORED_PREFIXES
    missing = sorted(p for p in fastapi_prefixes if p not in nginx_prefixes)
    assert not missing, (
        f"nginx.conf is missing FastAPI prefixes: {missing}. "
        f"Add them to docker/nginx.conf or browser /registry/* fetches will "
        f"receive index.html instead of JSON."
    )
