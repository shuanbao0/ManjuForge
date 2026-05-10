"""Integration tests for the Phase 3 ``*_async`` LLM endpoints.

Scope: HTTP-level wiring of the async one-shot routes — that they
return ``_task_id`` immediately, that the task lifecycle eventually
populates ``result``, and that input validation runs eagerly (before
the task is queued).

Tests that require a fully-persisted Script live in
``test_async_primitives.py`` (which exercises the lifecycle helpers
directly without going through the per-user pipeline_proxy).
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.apps.comic_gen import api as api_module
from src.apps.comic_gen.api import app


@pytest.fixture
def auth_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    db_path = tmp_path / "db" / "manjuforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MANJU_FORGE_DB_PATH", str(db_path))
    monkeypatch.setenv("MANJU_FORGE_JWT_SECRET", "test-jwt-secret-" + tmp_path.name)
    monkeypatch.setenv(
        "MANJU_FORGE_MASTER_KEY", "kZ2Hh7jfvJZbPq4_E1WZ9wQyOJ2aXt1kHUoQH9YwUqM="
    )
    from src.auth import db as auth_db
    auth_db.reset_for_tests()
    yield
    auth_db.reset_for_tests()


@pytest.fixture
def authed_client(auth_env) -> TestClient:
    """TestClient pre-authenticated as a fresh admin user."""
    client = TestClient(app)
    r = client.post(
        "/auth/setup",
        json={"email": "admin@example.com", "password": "passw0rd!", "display_name": "Boss"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _wait_for_task(client: TestClient, task_id: str, timeout: float = 2.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        res = client.get(f"/tasks/{task_id}")
        assert res.status_code == 200
        data = res.json()
        if data["status"] in ("completed", "failed"):
            return data
        time.sleep(0.05)
    pytest.fail(f"Task {task_id} did not complete in {timeout}s")


# === Routes that need no script context ==================================


def test_video_polish_prompt_async_returns_task_then_result(authed_client, monkeypatch):
    """``/video/polish_prompt_async`` is the simplest async route — no
    script lookup, just LLM call. Verifies the full submit→poll→result
    cycle wires up correctly through BackgroundTasks."""
    monkeypatch.setattr(
        "src.apps.comic_gen.api.ScriptProcessor",
        lambda: type("FakeProc", (), {
            "polish_video_prompt": lambda self, draft, fb, custom: {
                "prompt_cn": "动作", "prompt_en": "action",
            },
        })(),
    )

    r = authed_client.post(
        "/video/polish_prompt_async",
        json={"draft_prompt": "smile", "feedback": "", "script_id": ""},
    )
    assert r.status_code == 200
    tid = r.json()["_task_id"]
    final = _wait_for_task(authed_client, tid)
    assert final["status"] == "completed"
    assert final["result"] == {"prompt_cn": "动作", "prompt_en": "action"}


def test_video_polish_r2v_prompt_async(authed_client, monkeypatch):
    """Same shape as polish_prompt_async — second route, second sanity check."""
    monkeypatch.setattr(
        "src.apps.comic_gen.api.ScriptProcessor",
        lambda: type("FakeProc", (), {
            "polish_r2v_prompt": lambda self, draft, slots, fb, custom: {
                "prompt_cn": "演绎", "prompt_en": "perform",
            },
        })(),
    )
    r = authed_client.post(
        "/video/polish_r2v_prompt_async",
        json={"draft_prompt": "x", "slots": [{"description": "char A"}], "feedback": "", "script_id": ""},
    )
    assert r.status_code == 200
    final = _wait_for_task(authed_client, r.json()["_task_id"])
    assert final["status"] == "completed"
    assert final["result"]["prompt_en"] == "perform"


def test_video_polish_prompt_async_records_failure(authed_client, monkeypatch):
    """LLM failure should land in ``task['error']`` not in HTTP response —
    the POST must still 200 because the work hadn't started yet."""
    class ExplodingProcessor:
        def polish_video_prompt(self, *a, **kw):
            raise RuntimeError("vendor 500")

    monkeypatch.setattr("src.apps.comic_gen.api.ScriptProcessor", ExplodingProcessor)
    r = authed_client.post(
        "/video/polish_prompt_async",
        json={"draft_prompt": "x", "feedback": "", "script_id": ""},
    )
    assert r.status_code == 200
    final = _wait_for_task(authed_client, r.json()["_task_id"])
    assert final["status"] == "failed"
    assert "vendor 500" in final["error"]


# === series/import/confirm_async eager validation ========================


def test_series_import_confirm_async_400_on_no_text(authed_client):
    """Missing-text check runs *before* the task is queued so the user
    gets immediate feedback (vs. submitting and polling for failure)."""
    r = authed_client.post(
        "/series/import/confirm_async",
        json={"title": "t", "import_id": "", "text": None, "episodes": []},
    )
    assert r.status_code == 400


# === refine_prompt_async eager 404 =======================================


def test_refine_prompt_async_404_on_missing_script(authed_client):
    """Script-existence check runs eagerly; missing script must 404
    immediately without queuing a doomed task."""
    r = authed_client.post(
        "/projects/no_such_script/storyboard/refine_prompt_async",
        json={"frame_id": "f1", "raw_prompt": "x", "assets": [], "feedback": ""},
    )
    assert r.status_code == 404
