"""Lock in the ``?token=…`` escape hatch for ``/files/*``.

Browser ``<img src=...>`` tags can't attach a custom Authorization header,
so the auth middleware accepts a JWT in the query string for whitelisted
GET prefixes (currently ``/files/`` and ``/me/files/``). Other endpoints
must keep rejecting query-string tokens to avoid widening the JWT-leak
surface.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse


@pytest.fixture
def env_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    db_path = tmp_path / "db" / "manjuforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MANJU_FORGE_DB_PATH", str(db_path))
    monkeypatch.setenv("MANJU_FORGE_JWT_SECRET", "test-jwt-secret-" + tmp_path.name)
    monkeypatch.setenv("MANJU_FORGE_MASTER_KEY", "kZ2Hh7jfvJZbPq4_E1WZ9wQyOJ2aXt1kHUoQH9YwUqM=")

    from src.auth import db as auth_db

    auth_db.reset_for_tests()
    yield
    auth_db.reset_for_tests()


@pytest.fixture
def app_with_middleware(env_isolated) -> FastAPI:
    """Mini app: auth routes + a stub /files/* route + a stub /other/* route.

    Lets us assert that ``?token=…`` is honored on ``/files/`` GET but
    NOT on a generic protected route.
    """
    from src.auth import routes as auth_routes
    from src.auth.db import get_engine
    from src.auth.middleware import AuthContextMiddleware

    get_engine()
    app = FastAPI()
    app.add_middleware(AuthContextMiddleware)
    app.include_router(auth_routes.router)

    @app.get("/files/{rel_path:path}")
    async def fake_files(rel_path: str):
        return PlainTextResponse(f"served:{rel_path}")

    @app.get("/other/ping")
    async def fake_other():
        return PlainTextResponse("pong")

    return app


@pytest.fixture
def client(app_with_middleware: FastAPI) -> TestClient:
    return TestClient(app_with_middleware)


def _setup_admin(client: TestClient) -> str:
    r = client.post(
        "/auth/setup",
        json={"email": "admin@example.com", "password": "passw0rd!", "display_name": "Boss"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def test_files_route_accepts_query_string_token(client: TestClient):
    token = _setup_admin(client)
    r = client.get(f"/files/users/1/foo.png?token={token}")
    assert r.status_code == 200
    assert r.text == "served:users/1/foo.png"


def test_files_route_still_accepts_authorization_header(client: TestClient):
    token = _setup_admin(client)
    r = client.get(
        "/files/users/1/foo.png",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


def test_files_route_rejects_invalid_query_token(client: TestClient):
    _setup_admin(client)
    r = client.get("/files/users/1/foo.png?token=not-a-real-jwt")
    assert r.status_code == 401


def test_files_route_rejects_missing_token(client: TestClient):
    _setup_admin(client)
    r = client.get("/files/users/1/foo.png")
    assert r.status_code == 401


def test_other_endpoints_do_not_accept_query_token(client: TestClient):
    """Query-string token is opt-in per route prefix. A random protected
    endpoint should still demand the Authorization header."""
    token = _setup_admin(client)
    r = client.get(f"/other/ping?token={token}")
    assert r.status_code == 401


def test_other_endpoints_still_work_with_header(client: TestClient):
    token = _setup_admin(client)
    r = client.get("/other/ping", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
