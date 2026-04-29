"""End-to-end coverage for the auth + admin subsystems.

Each test gets a fresh on-disk SQLite DB (in tmp_path) so the tests are
fully isolated from any developer's real ~/.manju-forge install.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def env_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point instance secrets and DB at tmp_path; reset SQLAlchemy globals."""
    home = tmp_path / "home"
    home.mkdir()
    db_path = tmp_path / "db" / "manjuforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Pin home so get_user_data_dir() lands in tmp_path. Pin DB explicitly too.
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MANJU_FORGE_DB_PATH", str(db_path))
    # Pin secrets so generation is deterministic per test.
    monkeypatch.setenv("MANJU_FORGE_JWT_SECRET", "test-jwt-secret-" + tmp_path.name)
    monkeypatch.setenv("MANJU_FORGE_MASTER_KEY", "kZ2Hh7jfvJZbPq4_E1WZ9wQyOJ2aXt1kHUoQH9YwUqM=")

    # Force re-init of cached engine and instance secrets.
    from src.auth import db as auth_db
    auth_db.reset_for_tests()

    yield

    auth_db.reset_for_tests()


@pytest.fixture
def app(env_isolated) -> FastAPI:
    app = FastAPI()
    from src.auth import routes as auth_routes
    from src.admin import routes as admin_routes
    from src.auth.db import get_engine

    get_engine()  # eager schema create
    app.include_router(auth_routes.router)
    app.include_router(admin_routes.router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────


def _setup_admin(client: TestClient, email: str = "admin@example.com", password: str = "passw0rd!") -> str:
    r = client.post("/auth/setup", json={"email": email, "password": password, "display_name": "Boss"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Setup flow ────────────────────────────────────────────────────────────


def test_setup_status_initially_needs_setup(client: TestClient):
    r = client.get("/auth/setup-status")
    assert r.status_code == 200
    assert r.json() == {"needs_setup": True, "user_count": 0}


def test_setup_creates_first_admin_and_issues_token(client: TestClient):
    r = client.post("/auth/setup", json={"email": "a@b.com", "password": "pw12345678"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "admin"
    assert body["user"]["email"] == "a@b.com"
    assert body["access_token"]
    # Subsequent setup must be refused.
    r2 = client.post("/auth/setup", json={"email": "x@y.com", "password": "pw12345678"})
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "SETUP_ALREADY_COMPLETED"


def test_setup_validates_password_min_length(client: TestClient):
    r = client.post("/auth/setup", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422


# ── Login flow ────────────────────────────────────────────────────────────


def test_login_succeeds_with_correct_credentials(client: TestClient):
    _setup_admin(client)
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "passw0rd!"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_fails_with_wrong_password(client: TestClient):
    _setup_admin(client)
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "wrong-pw1"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_login_email_is_case_insensitive(client: TestClient):
    _setup_admin(client, email="Mixed@Case.com")
    r = client.post("/auth/login", json={"email": "MIXED@case.com", "password": "passw0rd!"})
    assert r.status_code == 200


# ── /auth/me & token enforcement ──────────────────────────────────────────


def test_me_requires_auth(client: TestClient):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_returns_user(client: TestClient):
    token = _setup_admin(client)
    r = client.get("/auth/me", headers=_bearer(token))
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_invalid_token_rejected(client: TestClient):
    _setup_admin(client)
    r = client.get("/auth/me", headers=_bearer("garbage.token.value"))
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_TOKEN"


# ── Password change rotates token_version ─────────────────────────────────


def test_password_change_invalidates_old_token(client: TestClient):
    old_token = _setup_admin(client)
    r = client.post(
        "/auth/password",
        json={"current_password": "passw0rd!", "new_password": "newpassw0rd!"},
        headers=_bearer(old_token),
    )
    assert r.status_code == 200
    new_token = r.json()["access_token"]
    assert new_token != old_token

    # Old token should be revoked.
    r_old = client.get("/auth/me", headers=_bearer(old_token))
    assert r_old.status_code == 401
    assert r_old.json()["detail"]["code"] == "TOKEN_REVOKED"

    # New token works.
    r_new = client.get("/auth/me", headers=_bearer(new_token))
    assert r_new.status_code == 200


def test_password_change_requires_correct_current(client: TestClient):
    token = _setup_admin(client)
    r = client.post(
        "/auth/password",
        json={"current_password": "wrong-pw1", "new_password": "newpassw0rd!"},
        headers=_bearer(token),
    )
    assert r.status_code == 401


# ── Logout invalidates token ──────────────────────────────────────────────


def test_logout_invalidates_token(client: TestClient):
    token = _setup_admin(client)
    r = client.post("/auth/logout", headers=_bearer(token))
    assert r.status_code == 204
    r2 = client.get("/auth/me", headers=_bearer(token))
    assert r2.status_code == 401


# ── Admin user CRUD ───────────────────────────────────────────────────────


def test_admin_list_create_update_delete_user(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)

    # Initially only the admin exists.
    r = client.get("/admin/users", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Create a regular user.
    r = client.post(
        "/admin/users",
        json={"email": "alice@example.com", "password": "alicepassw0rd", "role": "user"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    alice_id = r.json()["id"]

    # Get one.
    r = client.get(f"/admin/users/{alice_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"

    # Update display name + reset password.
    r = client.patch(
        f"/admin/users/{alice_id}",
        json={"display_name": "Alice", "new_password": "freshpassw0rd"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Alice"

    # Alice can log in with new password.
    r = client.post("/auth/login", json={"email": "alice@example.com", "password": "freshpassw0rd"})
    assert r.status_code == 200
    alice_token = r.json()["access_token"]

    # Disable user → they can no longer use their token.
    r = client.patch(f"/admin/users/{alice_id}", json={"status": "disabled"}, headers=h)
    assert r.status_code == 200
    r = client.get("/auth/me", headers=_bearer(alice_token))
    assert r.status_code == 401

    # Re-enable then delete.
    r = client.patch(f"/admin/users/{alice_id}", json={"status": "active"}, headers=h)
    assert r.status_code == 200
    r = client.delete(f"/admin/users/{alice_id}", headers=h)
    assert r.status_code == 204

    # List shows admin only again.
    r = client.get("/admin/users", headers=h)
    assert len(r.json()) == 1


def test_admin_cannot_demote_last_admin(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)
    r = client.get("/auth/me", headers=h)
    admin_id = r.json()["id"]

    r = client.patch(f"/admin/users/{admin_id}", json={"role": "user"}, headers=h)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "CANNOT_DEMOTE_LAST_ADMIN"


def test_admin_cannot_delete_self(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)
    me = client.get("/auth/me", headers=h).json()
    r = client.delete(f"/admin/users/{me['id']}", headers=h)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "CANNOT_DELETE_SELF"


def test_admin_force_logout_revokes_target_tokens(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)

    client.post(
        "/admin/users",
        json={"email": "bob@example.com", "password": "bobpassw0rd", "role": "user"},
        headers=h,
    )
    bob_login = client.post("/auth/login", json={"email": "bob@example.com", "password": "bobpassw0rd"}).json()
    bob_token = bob_login["access_token"]
    bob_id = bob_login["user"]["id"]

    # Bob is logged in.
    assert client.get("/auth/me", headers=_bearer(bob_token)).status_code == 200

    # Admin force-logs Bob out.
    r = client.post(f"/admin/users/{bob_id}/force-logout", headers=h)
    assert r.status_code == 200

    # Bob's token now revoked.
    r = client.get("/auth/me", headers=_bearer(bob_token))
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "TOKEN_REVOKED"


def test_non_admin_cannot_access_admin_routes(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)
    client.post(
        "/admin/users",
        json={"email": "carol@example.com", "password": "carolpassw0rd", "role": "user"},
        headers=h,
    )
    user_token = client.post(
        "/auth/login", json={"email": "carol@example.com", "password": "carolpassw0rd"}
    ).json()["access_token"]

    for method, path in [
        ("GET", "/admin/users"),
        ("POST", "/admin/users"),
        ("GET", "/admin/stats"),
        ("GET", "/admin/audit-logs"),
        ("GET", "/admin/settings"),
    ]:
        r = client.request(method, path, json={} if method == "POST" else None, headers=_bearer(user_token))
        assert r.status_code == 403, f"{method} {path} expected 403, got {r.status_code}"


def test_create_user_rejects_duplicate_email(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)
    client.post(
        "/admin/users",
        json={"email": "dup@example.com", "password": "duppassw0rd", "role": "user"},
        headers=h,
    )
    r = client.post(
        "/admin/users",
        json={"email": "dup@example.com", "password": "duppassw0rd", "role": "user"},
        headers=h,
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "EMAIL_EXISTS"


# ── Stats / settings / audit ──────────────────────────────────────────────


def test_admin_stats(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)
    client.post(
        "/admin/users",
        json={"email": "u1@example.com", "password": "pw12345678", "role": "user"},
        headers=h,
    )
    r = client.get("/admin/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["user_count"] == 2
    assert body["active_user_count"] == 2
    assert body["admin_count"] == 1


def test_settings_round_trip(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)
    r = client.get("/admin/settings", headers=h)
    assert r.json()["registration_enabled"] is False

    r = client.put(
        "/admin/settings",
        json={"registration_enabled": True, "default_user_role": "user"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["registration_enabled"] is True

    r = client.get("/admin/settings", headers=h)
    assert r.json()["registration_enabled"] is True


def test_audit_log_records_login_and_admin_actions(client: TestClient):
    admin_token = _setup_admin(client)
    h = _bearer(admin_token)
    client.post("/auth/login", json={"email": "admin@example.com", "password": "passw0rd!"})
    client.post(
        "/admin/users",
        json={"email": "audit@example.com", "password": "auditpassw0rd", "role": "user"},
        headers=h,
    )
    r = client.get("/admin/audit-logs", headers=h)
    assert r.status_code == 200
    actions = [e["action"] for e in r.json()]
    assert "auth.setup" in actions
    assert "auth.login" in actions
    assert "admin.user.create" in actions
