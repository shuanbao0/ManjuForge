"""End-to-end tests for /me/instances CRUD + test + set-default."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── Fixtures (mirror test_auth.py pattern) ────────────────────────────────


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
def app(env_isolated) -> FastAPI:
    app = FastAPI()
    from src.auth import routes as auth_routes
    from src.auth import me_routes as me_routes_module
    from src.auth.db import get_engine

    get_engine()
    app.include_router(auth_routes.router)
    app.include_router(me_routes_module.router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _setup_admin(client: TestClient) -> str:
    r = client.post("/auth/setup", json={"email": "admin@x.io", "password": "pw1234567!", "display_name": "A"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _new_user(client: TestClient, admin_token: str, email: str = "u@x.io") -> str:
    """Create another user; returns their access token."""
    r = client.post(
        "/auth/admin/users",
        json={"email": email, "password": "pw1234567!", "role": "user", "display_name": "U"},
        headers=_bearer(admin_token),
    )
    if r.status_code == 404:
        # admin/users not under /auth — try /admin
        r = client.post(
            "/admin/users",
            json={"email": email, "password": "pw1234567!", "role": "user", "display_name": "U"},
            headers=_bearer(admin_token),
        )
    # Login as that user
    r = client.post("/auth/login", json={"email": email, "password": "pw1234567!"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _payload(**overrides):
    base = dict(
        instance_type="llm",
        vendor_id="openai",
        model_name="gpt-5",
        display_name="工作室主力",
        credentials={"OPENAI_API_KEY": "sk-test"},
        is_default=False,
    )
    base.update(overrides)
    return base


# ── CRUD ─────────────────────────────────────────────────────────────────


def test_setup_seeds_default_instances(client: TestClient):
    """Onboarding creates one default ModelInstance per type so the
    Settings UI never starts blank."""
    token = _setup_admin(client)
    r = client.get("/me/instances", headers=_bearer(token))
    assert r.status_code == 200
    instances = r.json()
    types_seen = {i["instance_type"] for i in instances}
    assert types_seen == {"llm", "t2i", "i2i", "i2v", "tts"}
    assert all(i["is_default"] for i in instances)
    # Credentials start empty — user fills them in via the wizard.
    assert all(i["credential_keys"] == [] for i in instances)


def test_create_then_list_and_get(client: TestClient):
    token = _setup_admin(client)
    seeded_count = len(client.get("/me/instances", headers=_bearer(token)).json())

    r = client.post("/me/instances", json=_payload(), headers=_bearer(token))
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["display_name"] == "工作室主力"
    assert created["credential_keys"] == ["OPENAI_API_KEY"]
    assert "credentials" not in created  # never leak the secret

    r = client.get("/me/instances", headers=_bearer(token))
    assert r.status_code == 200
    listing = r.json()
    assert len(listing) == seeded_count + 1
    assert any(i["id"] == created["id"] for i in listing)

    r = client.get(f"/me/instances/{created['id']}", headers=_bearer(token))
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_filter_by_type(client: TestClient):
    token = _setup_admin(client)
    client.post("/me/instances", json=_payload(instance_type="llm"), headers=_bearer(token))
    client.post("/me/instances", json=_payload(instance_type="t2i", vendor_id="dashscope", model_name="wan2.6-t2i"), headers=_bearer(token))
    # Seed adds 1 LLM + 1 T2I + others. Created adds 1 LLM + 1 T2I.
    r = client.get("/me/instances?type=llm", headers=_bearer(token))
    assert r.status_code == 200
    llms = r.json()
    assert len(llms) == 2
    assert all(i["instance_type"] == "llm" for i in llms)


def test_create_rejects_unknown_type(client: TestClient):
    token = _setup_admin(client)
    r = client.post("/me/instances", json=_payload(instance_type="bogus"), headers=_bearer(token))
    assert r.status_code == 400


def test_update_changes_only_provided(client: TestClient):
    token = _setup_admin(client)
    inst = client.post("/me/instances", json=_payload(), headers=_bearer(token)).json()
    r = client.put(
        f"/me/instances/{inst['id']}",
        json={"display_name": "renamed", "base_url": "http://new"},
        headers=_bearer(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "renamed"
    assert body["base_url"] == "http://new"
    assert body["model_name"] == "gpt-5"  # untouched


def test_delete_then_404(client: TestClient):
    token = _setup_admin(client)
    inst = client.post("/me/instances", json=_payload(), headers=_bearer(token)).json()
    r = client.delete(f"/me/instances/{inst['id']}", headers=_bearer(token))
    assert r.status_code == 204
    r = client.get(f"/me/instances/{inst['id']}", headers=_bearer(token))
    assert r.status_code == 404


def test_set_default_promotes_one_demotes_others(client: TestClient):
    token = _setup_admin(client)
    a = client.post("/me/instances", json=_payload(model_name="gpt-5", is_default=True), headers=_bearer(token)).json()
    b = client.post("/me/instances", json=_payload(model_name="claude-opus-4-7"), headers=_bearer(token)).json()
    r = client.post(f"/me/instances/{b['id']}/set-default", headers=_bearer(token))
    assert r.status_code == 200
    assert r.json()["is_default"] is True
    assert client.get(f"/me/instances/{a['id']}", headers=_bearer(token)).json()["is_default"] is False


def test_test_endpoint_reports_dashscope_key_missing(client: TestClient):
    token = _setup_admin(client)
    inst = client.post(
        "/me/instances",
        json=_payload(instance_type="t2i", vendor_id="dashscope", model_name="wan2.6-t2i", credentials={}),
        headers=_bearer(token),
    ).json()
    r = client.post(f"/me/instances/{inst['id']}/test", headers=_bearer(token))
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "DASHSCOPE_API_KEY" in body["error"]


def test_test_endpoint_passes_when_dashscope_key_set(client: TestClient):
    token = _setup_admin(client)
    inst = client.post(
        "/me/instances",
        json=_payload(
            instance_type="t2i", vendor_id="dashscope", model_name="wan2.6-t2i",
            credentials={"DASHSCOPE_API_KEY": "sk-yes"},
        ),
        headers=_bearer(token),
    ).json()
    r = client.post(f"/me/instances/{inst['id']}/test", headers=_bearer(token))
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_unauthorized_cannot_list(client: TestClient):
    r = client.get("/me/instances")
    assert r.status_code == 401
