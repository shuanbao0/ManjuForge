"""Tests for the async export task wrapper around merge_videos."""
import time
from types import SimpleNamespace

import pytest

from src.apps.comic_gen.models import ModelSettings, Script
from src.apps.comic_gen.pipeline import ComicGenPipeline


def _bare_pipeline_with_script(merged_url=None):
    now = time.time()
    script = Script(
        id="proj1",
        title="t",
        original_text="",
        characters=[],
        scenes=[],
        frames=[],
        model_settings=ModelSettings(),
        created_at=now,
        updated_at=now,
    )
    if merged_url:
        script.merged_video_url = merged_url

    p = ComicGenPipeline.__new__(ComicGenPipeline)
    p.scripts = {script.id: script}
    p.asset_generation_tasks = {}
    p.video_generation_tasks = {}
    p._save_data = lambda: None
    p.data_root = "output"
    return p, script


def test_create_task_envelope_has_export_fields():
    p, _ = _bare_pipeline_with_script()
    _, tid = p.create_export_task("proj1", params={})
    task = p.asset_generation_tasks[tid]
    assert task["task_type"] == "export"
    assert task["current_stage"] == "pending"
    assert task["output_url"] is None


def test_cached_merge_short_circuits_to_completed():
    """If merged_video_url already exists and force is not set, the task
    should mark itself completed in create_export_task — no FFmpeg run."""
    p, _ = _bare_pipeline_with_script(merged_url="videos/cached.mp4")
    _, tid = p.create_export_task("proj1", params={})
    task = p.asset_generation_tasks[tid]
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["current_stage"] == "cached"
    assert task["output_url"] == "videos/cached.mp4"


def test_force_param_skips_cache():
    p, _ = _bare_pipeline_with_script(merged_url="videos/cached.mp4")
    _, tid = p.create_export_task("proj1", params={"force": True})
    task = p.asset_generation_tasks[tid]
    # Should NOT have short-circuited.
    assert task["status"] == "pending"
    assert task["current_stage"] == "pending"


def test_process_task_walks_3_stages_on_success(monkeypatch):
    p, script = _bare_pipeline_with_script()
    stages_seen = []

    def fake_merge(script_id):
        stages_seen.append(p.asset_generation_tasks[tid]["current_stage"])
        script.merged_video_url = "videos/output.mp4"
        return script

    p.merge_videos = fake_merge
    _, tid = p.create_export_task("proj1", params={})
    p.process_export_task(tid)

    task = p.asset_generation_tasks[tid]
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["output_url"] == "videos/output.mp4"
    # Worker bumps to "ffmpeg" before calling merge_videos.
    assert stages_seen == ["ffmpeg"]


def test_process_task_records_error_on_ffmpeg_failure():
    p, _ = _bare_pipeline_with_script()
    p.merge_videos = lambda sid: (_ for _ in ()).throw(RuntimeError("ffmpeg explosion"))
    _, tid = p.create_export_task("proj1", params={})
    p.process_export_task(tid)
    task = p.asset_generation_tasks[tid]
    assert task["status"] == "failed"
    assert task["error"] == "ffmpeg explosion"
    # On failure output_url stays None so the UI knows not to show download.
    assert task["output_url"] is None


def test_process_task_skips_work_for_cached_completion():
    """Cached-result task is already completed; the worker should be a no-op."""
    p, _ = _bare_pipeline_with_script(merged_url="videos/cached.mp4")
    p.merge_videos = lambda sid: pytest.fail("merge_videos should not be called")
    _, tid = p.create_export_task("proj1", params={})
    p.process_export_task(tid)
    assert p.asset_generation_tasks[tid]["status"] == "completed"


def test_status_endpoint_surfaces_export_fields():
    p, _ = _bare_pipeline_with_script(merged_url="videos/cached.mp4")
    _, tid = p.create_export_task("proj1", params={})
    status = p.get_asset_generation_task_status(tid)
    assert status["task_type"] == "export"
    assert status["current_stage"] == "cached"
    assert status["output_url"] == "videos/cached.mp4"


def test_create_task_404_on_missing_script():
    p, _ = _bare_pipeline_with_script()
    with pytest.raises(ValueError, match="Script not found"):
        p.create_export_task("nonexistent", params={})
