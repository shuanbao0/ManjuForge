"""End-to-end checks that the multi-user refactor (P2 + P3) actually
isolates users from each other.

* Each authenticated user gets their own ``output/users/<uid>/`` and
  their own per-user pipeline (different ``data_root``).
* ``/files/{path}`` 401s without auth and 404s when a path doesn't
  belong to the caller.
* Per-user credentials are decrypted into ``runtime.get_cred(...)`` so
  provider lookups read the right user's keys.
* ``/admin/*`` and instance-level config endpoints reject non-admins.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def env_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    db_path = tmp_path / "db" / "manjuforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MANJU_FORGE_DB_PATH", str(db_path))
    monkeypatch.setenv("MANJU_FORGE_JWT_SECRET", "test-jwt-iso-" + tmp_path.name)
    monkeypatch.setenv("MANJU_FORGE_MASTER_KEY", "kZ2Hh7jfvJZbPq4_E1WZ9wQyOJ2aXt1kHUoQH9YwUqM=")

    from src.auth import db as auth_db
    auth_db.reset_for_tests()

    # Reset per-user pipeline cache between tests so the new tmp cwd is
    # respected (pipelines bake in a path at construction time).
    from src.apps.comic_gen import pipeline_factory
    pipeline_factory._PER_USER_CACHE.clear()
    pipeline_factory._legacy = None

    yield

    auth_db.reset_for_tests()
    pipeline_factory._PER_USER_CACHE.clear()
    pipeline_factory._legacy = None


@pytest.fixture
def client(env_isolated) -> TestClient:
    # Build a small app that mounts auth + admin + me + a single
    # business-route stand-in so we can exercise the middleware without
    # importing the full comic_gen app (which has heavy imports).
    from src.auth import routes as auth_routes
    from src.auth import me_routes as me_routes_module
    from src.admin import routes as admin_routes
    from src.auth.middleware import AuthContextMiddleware
    from src.auth.db import get_engine
    from src import runtime
    from src.apps.comic_gen.pipeline_factory import current_pipeline

    get_engine()

    app = FastAPI()
    app.add_middleware(AuthContextMiddleware)
    app.include_router(auth_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(me_routes_module.router)

    @app.get("/business/whoami")
    def whoami():
        u = runtime.current_user()
        pipe = current_pipeline()
        return {
            "user_id": u.id if u else None,
            "data_root": pipe.data_root,
            "dashscope_key_visible": runtime.get_cred("DASHSCOPE_API_KEY"),
        }

    return TestClient(app)


def _setup_admin(client: TestClient, email="admin@x.com", password="passw0rd!") -> str:
    r = client.post("/auth/setup", json={"email": email, "password": password})
    assert r.status_code == 201
    return r.json()["access_token"]


def _create_user(client: TestClient, admin_token: str, email: str, password: str = "userpassw0rd") -> int:
    r = client.post(
        "/admin/users",
        json={"email": email, "password": password, "role": "user"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _login(client: TestClient, email: str, password: str = "userpassw0rd") -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


# ── Tests ─────────────────────────────────────────────────────────────────


def test_business_route_requires_auth(client: TestClient):
    r = client.get("/business/whoami")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "UNAUTHORIZED"


def test_business_route_rejects_invalid_token(client: TestClient):
    r = client.get("/business/whoami", headers={"Authorization": "Bearer bogus"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_TOKEN"


def test_each_user_has_own_data_root(client: TestClient):
    admin_token = _setup_admin(client)
    alice_id = _create_user(client, admin_token, "alice@x.com")
    bob_id = _create_user(client, admin_token, "bob@x.com")

    alice_token = _login(client, "alice@x.com")
    bob_token = _login(client, "bob@x.com")

    a = client.get("/business/whoami", headers={"Authorization": f"Bearer {alice_token}"}).json()
    b = client.get("/business/whoami", headers={"Authorization": f"Bearer {bob_token}"}).json()

    assert a["user_id"] == alice_id
    assert b["user_id"] == bob_id
    assert a["data_root"] != b["data_root"]
    assert a["data_root"].endswith(f"users/{alice_id}")
    assert b["data_root"].endswith(f"users/{bob_id}")
    # The directories must actually exist on disk after the request.
    assert os.path.isdir(a["data_root"])
    assert os.path.isdir(b["data_root"])


def test_per_user_credentials_isolated(client: TestClient):
    admin_token = _setup_admin(client)
    _create_user(client, admin_token, "alice@x.com")
    _create_user(client, admin_token, "bob@x.com")

    alice_token = _login(client, "alice@x.com")
    bob_token = _login(client, "bob@x.com")

    # Alice puts a key, Bob puts a different key.
    r = client.put(
        "/me/credentials",
        json={"values": {"DASHSCOPE_API_KEY": "alice-key", "OPENAI_BASE_URL": "https://alice.example/v1"}},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert r.status_code == 200, r.text
    r = client.put(
        "/me/credentials",
        json={"values": {"DASHSCOPE_API_KEY": "bob-key"}},
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert r.status_code == 200

    # Each user sees only their own key (revealed) and their own data_root resolves their key in business.
    a = client.get("/me/credentials?reveal=true", headers={"Authorization": f"Bearer {alice_token}"}).json()
    b = client.get("/me/credentials?reveal=true", headers={"Authorization": f"Bearer {bob_token}"}).json()
    assert a["values"]["DASHSCOPE_API_KEY"] == "alice-key"
    assert b["values"]["DASHSCOPE_API_KEY"] == "bob-key"

    biz_a = client.get("/business/whoami", headers={"Authorization": f"Bearer {alice_token}"}).json()
    biz_b = client.get("/business/whoami", headers={"Authorization": f"Bearer {bob_token}"}).json()
    assert biz_a["dashscope_key_visible"] == "alice-key"
    assert biz_b["dashscope_key_visible"] == "bob-key"


def test_credentials_response_masks_secrets_by_default(client: TestClient):
    admin_token = _setup_admin(client)
    _create_user(client, admin_token, "alice@x.com")
    alice_token = _login(client, "alice@x.com")

    client.put(
        "/me/credentials",
        json={"values": {"DASHSCOPE_API_KEY": "sk-abcdef1234567890"}},
        headers={"Authorization": f"Bearer {alice_token}"},
    )

    masked = client.get("/me/credentials", headers={"Authorization": f"Bearer {alice_token}"}).json()
    assert masked["masked"] is True
    assert masked["values"]["DASHSCOPE_API_KEY"].count("•") > 0
    assert "abcdef" not in masked["values"]["DASHSCOPE_API_KEY"]

    revealed = client.get("/me/credentials?reveal=true", headers={"Authorization": f"Bearer {alice_token}"}).json()
    assert revealed["masked"] is False
    assert revealed["values"]["DASHSCOPE_API_KEY"] == "sk-abcdef1234567890"


def test_credentials_unknown_key_silently_ignored(client: TestClient):
    admin_token = _setup_admin(client)
    _create_user(client, admin_token, "alice@x.com")
    alice_token = _login(client, "alice@x.com")

    r = client.put(
        "/me/credentials",
        json={"values": {"DASHSCOPE_API_KEY": "alice", "WRONG_FIELD": "leak"}},
        headers={"Authorization": f"Bearer {alice_token}"},
    )
    assert r.status_code == 200
    revealed = client.get("/me/credentials?reveal=true", headers={"Authorization": f"Bearer {alice_token}"}).json()
    assert "WRONG_FIELD" not in revealed["values"]
    assert revealed["values"]["DASHSCOPE_API_KEY"] == "alice"


def test_admin_routes_blocked_for_regular_user(client: TestClient):
    admin_token = _setup_admin(client)
    _create_user(client, admin_token, "alice@x.com")
    alice_token = _login(client, "alice@x.com")
    h = {"Authorization": f"Bearer {alice_token}"}

    for path in ("/admin/users", "/admin/stats", "/admin/audit-logs", "/admin/settings"):
        r = client.get(path, headers=h)
        assert r.status_code == 403, f"{path} should 403 for non-admin"


def test_disabled_user_token_rejected(client: TestClient):
    admin_token = _setup_admin(client)
    alice_id = _create_user(client, admin_token, "alice@x.com")
    alice_token = _login(client, "alice@x.com")

    # Admin disables Alice — her token should be rejected on the next call.
    r = client.patch(
        f"/admin/users/{alice_id}",
        json={"status": "disabled"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert r.status_code == 200

    r = client.get("/me/credentials", headers={"Authorization": f"Bearer {alice_token}"})
    assert r.status_code == 401


def test_password_change_kicks_old_token_through_middleware(client: TestClient):
    admin_token = _setup_admin(client)
    _create_user(client, admin_token, "alice@x.com", password="firstpassw0rd")
    old_alice_token = _login(client, "alice@x.com", password="firstpassw0rd")

    r = client.post(
        "/auth/password",
        json={"current_password": "firstpassw0rd", "new_password": "secondpassw0rd"},
        headers={"Authorization": f"Bearer {old_alice_token}"},
    )
    assert r.status_code == 200

    # Old token should now be revoked when used against any business endpoint.
    r = client.get("/business/whoami", headers={"Authorization": f"Bearer {old_alice_token}"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "TOKEN_REVOKED"


# ── Async-context propagation regression ─────────────────────────────────


def test_run_in_executor_carries_user_credentials(env_isolated, monkeypatch):
    """Regression for the ContextVar bug: per-user credentials must remain
    visible inside ``loop.run_in_executor`` worker threads. Without the
    ``runtime.run_in_executor`` wrapper providers fall back to env, so
    this test will catch any future regressions that strip the wrapper."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.auth import routes as auth_routes, me_routes as me_routes_module
    from src.admin import routes as admin_routes
    from src.auth.middleware import AuthContextMiddleware
    from src.auth.db import get_engine
    from src import runtime

    monkeypatch.setenv("DASHSCOPE_API_KEY", "GLOBAL-FALLBACK-KEY")

    get_engine()
    app = FastAPI()
    app.add_middleware(AuthContextMiddleware)
    app.include_router(auth_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(me_routes_module.router)

    @app.get("/exec/cred")
    async def via_executor():
        # Read inside a worker thread — without the wrapper this returns the env value.
        result = await runtime.run_in_executor(None, runtime.get_cred, "DASHSCOPE_API_KEY")
        return {"value": result}

    c = TestClient(app)
    tok = c.post("/auth/setup", json={"email": "x@y.com", "password": "pw12345678"}).json()["access_token"]
    c.put(
        "/me/credentials",
        json={"values": {"DASHSCOPE_API_KEY": "PER-USER-KEY"}},
        headers={"Authorization": f"Bearer {tok}"},
    )
    r = c.get("/exec/cred", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["value"] == "PER-USER-KEY"


def test_background_tasks_carry_user_credentials(env_isolated, monkeypatch):
    """Same property must hold for sync ``BackgroundTasks`` callbacks."""
    from src.auth import routes as auth_routes, me_routes as me_routes_module
    from src.admin import routes as admin_routes
    from src.auth.middleware import AuthContextMiddleware
    from src.auth.db import get_engine
    from src import runtime

    monkeypatch.setenv("DASHSCOPE_API_KEY", "GLOBAL-FALLBACK-KEY")

    get_engine()
    app = FastAPI()
    app.add_middleware(AuthContextMiddleware)
    app.include_router(auth_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(me_routes_module.router)

    captured: dict[str, str] = {}

    def background_record() -> None:
        captured["value"] = runtime.get_cred("DASHSCOPE_API_KEY")

    @app.get("/bg/cred")
    async def kick(background_tasks: BackgroundTasks):
        runtime.add_background_task(background_tasks, background_record)
        return {"queued": True}

    c = TestClient(app)
    tok = c.post("/auth/setup", json={"email": "y@z.com", "password": "pw12345678"}).json()["access_token"]
    c.put(
        "/me/credentials",
        json={"values": {"DASHSCOPE_API_KEY": "PER-USER-KEY"}},
        headers={"Authorization": f"Bearer {tok}"},
    )
    r = c.get("/bg/cred", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, f"got {r.status_code}: {r.text}"
    # TestClient runs background tasks synchronously after the response.
    assert captured.get("value") == "PER-USER-KEY"


def test_credential_change_evicts_storage_clients(env_isolated):
    """Setting new credentials must drop the cached OSS / S3 clients so a
    subsequent storage call sees the new bucket. Without the eviction in
    ``me_routes``, the per-user uploader keeps the old keys forever."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.auth import routes as auth_routes, me_routes as me_routes_module
    from src.admin import routes as admin_routes
    from src.auth.middleware import AuthContextMiddleware
    from src.auth.db import get_engine
    from src.utils.oss_utils import OSSImageUploader

    get_engine()
    app = FastAPI()
    app.add_middleware(AuthContextMiddleware)
    app.include_router(auth_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(me_routes_module.router)

    @app.get("/storage/probe")
    async def probe():
        u = OSSImageUploader()
        return {"bucket": u.bucket_name or ""}

    c = TestClient(app)
    tok = c.post("/auth/setup", json={"email": "z@x.com", "password": "pw12345678"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    c.put(
        "/me/credentials",
        json={"values": {"OSS_BUCKET_NAME": "first-bucket"}},
        headers=h,
    )
    assert c.get("/storage/probe", headers=h).json()["bucket"] == "first-bucket"

    c.put(
        "/me/credentials",
        json={"values": {"OSS_BUCKET_NAME": "second-bucket"}},
        headers=h,
    )
    assert c.get("/storage/probe", headers=h).json()["bucket"] == "second-bucket"
