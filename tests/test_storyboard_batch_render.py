"""Unit tests for the async storyboard batch-render pipeline.

Covers the predicate (``_should_render_frame``), task lifecycle
(``create_storyboard_batch_render_task`` /
``process_storyboard_batch_render_task``), and per-frame failure
isolation. The actual model call is monkeypatched so tests stay
fast and offline.
"""
import time
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from src.apps.comic_gen.models import (
    GenerationStatus,
    ModelSettings,
    Script,
    StoryboardFrame,
)
from src.apps.comic_gen.pipeline import ComicGenPipeline


# === Predicate ============================================================


def test_predicate_locked_frame_never_rendered():
    f = StoryboardFrame(id="f1", scene_id="s1", locked=True)
    assert ComicGenPipeline._should_render_frame(f) is False
    # Locked overrides force — this is the user's "don't touch" signal.
    assert ComicGenPipeline._should_render_frame(f, force=True) is False


def test_predicate_pending_frame_eligible():
    f = StoryboardFrame(id="f2", scene_id="s1")
    assert ComicGenPipeline._should_render_frame(f) is True


def test_predicate_completed_frame_skipped_unless_force():
    f = StoryboardFrame(id="f3", scene_id="s1", image_url="output/storyboard/x.png")
    assert ComicGenPipeline._should_render_frame(f) is False
    assert ComicGenPipeline._should_render_frame(f, force=True) is True


def test_predicate_recognizes_rendered_image_url():
    f = StoryboardFrame(id="f4", scene_id="s1", rendered_image_url="output/storyboard/y.png")
    assert ComicGenPipeline._should_render_frame(f) is False


# === Batch task ===========================================================


def _make_pipeline_with_script(frames):
    now = time.time()
    script = Script(
        id="proj1",
        title="t",
        original_text="",
        characters=[],
        scenes=[],
        frames=frames,
        model_settings=ModelSettings(),
        created_at=now,
        updated_at=now,
    )
    p = ComicGenPipeline.__new__(ComicGenPipeline)
    p.scripts = {script.id: script}
    p.asset_generation_tasks = {}
    p.video_generation_tasks = {}
    p._save_data = lambda: None
    p.data_root = "output"
    p.storyboard_generator = SimpleNamespace()  # filled per-test
    return p, script


def test_create_task_counts_pending_frames():
    p, _ = _make_pipeline_with_script([
        StoryboardFrame(id="a", scene_id="s1"),                              # pending
        StoryboardFrame(id="b", scene_id="s1", image_url="x.png"),           # done
        StoryboardFrame(id="c", scene_id="s1", locked=True),                 # locked
        StoryboardFrame(id="d", scene_id="s1"),                              # pending
    ])
    _, task_id = p.create_storyboard_batch_render_task("proj1", force=False)
    task = p.asset_generation_tasks[task_id]
    assert task["total_count"] == 4
    assert task["pending_count"] == 2
    assert task["status"] == "pending"


def test_create_task_with_force_includes_completed_but_not_locked():
    p, _ = _make_pipeline_with_script([
        StoryboardFrame(id="a", scene_id="s1", image_url="x.png"),
        StoryboardFrame(id="b", scene_id="s1", locked=True),
    ])
    _, task_id = p.create_storyboard_batch_render_task("proj1", force=True)
    assert p.asset_generation_tasks[task_id]["pending_count"] == 1


def test_process_task_skips_already_rendered_and_locked():
    p, script = _make_pipeline_with_script([
        StoryboardFrame(id="a", scene_id="s1"),
        StoryboardFrame(id="b", scene_id="s1", image_url="x.png"),
        StoryboardFrame(id="c", scene_id="s1", locked=True),
    ])
    rendered_ids = []
    p._render_single_frame = lambda script, frame: rendered_ids.append(frame.id)

    _, task_id = p.create_storyboard_batch_render_task("proj1", force=False)
    p.process_storyboard_batch_render_task(task_id)

    assert rendered_ids == ["a"]
    task = p.asset_generation_tasks[task_id]
    assert task["status"] == "completed"
    assert task["progress"] == 100
    assert task["completed_count"] == 1
    assert task["failed_count"] == 0


def test_process_task_isolates_per_frame_failure():
    p, _ = _make_pipeline_with_script([
        StoryboardFrame(id="a", scene_id="s1"),
        StoryboardFrame(id="b", scene_id="s1"),
        StoryboardFrame(id="c", scene_id="s1"),
    ])

    def render(script, frame):
        if frame.id == "b":
            raise RuntimeError("boom")

    p._render_single_frame = render
    _, task_id = p.create_storyboard_batch_render_task("proj1")
    p.process_storyboard_batch_render_task(task_id)

    task = p.asset_generation_tasks[task_id]
    # Failure of one frame doesn't tank the rest.
    assert task["status"] == "completed"
    assert task["completed_count"] == 2
    assert task["failed_count"] == 1
    assert "b" in task["errors"]
    assert "boom" in task["errors"]["b"]


def test_process_task_with_no_pending_completes_immediately():
    p, _ = _make_pipeline_with_script([
        StoryboardFrame(id="a", scene_id="s1", image_url="x.png"),
        StoryboardFrame(id="b", scene_id="s1", locked=True),
    ])
    p._render_single_frame = lambda *a, **kw: pytest.fail("should not be called")
    _, task_id = p.create_storyboard_batch_render_task("proj1")
    p.process_storyboard_batch_render_task(task_id)
    task = p.asset_generation_tasks[task_id]
    assert task["status"] == "completed"
    assert task["progress"] == 100


def test_progress_reaches_100_for_partial_failures():
    p, _ = _make_pipeline_with_script([
        StoryboardFrame(id=f"f{i}", scene_id="s1") for i in range(4)
    ])
    p._render_single_frame = lambda script, frame: (_ for _ in ()).throw(RuntimeError("x"))
    _, task_id = p.create_storyboard_batch_render_task("proj1")
    p.process_storyboard_batch_render_task(task_id)
    assert p.asset_generation_tasks[task_id]["progress"] == 100
    assert p.asset_generation_tasks[task_id]["failed_count"] == 4


# === Status surface =======================================================


def test_get_task_status_surfaces_batch_fields():
    p, _ = _make_pipeline_with_script([StoryboardFrame(id="a", scene_id="s1")])
    p._render_single_frame = lambda script, frame: None
    _, task_id = p.create_storyboard_batch_render_task("proj1")
    p.process_storyboard_batch_render_task(task_id)

    status = p.get_asset_generation_task_status(task_id)
    # The /tasks/{id} endpoint relies on these keys.
    assert status["task_type"] == "storyboard_batch_render"
    assert status["completed_count"] == 1
    assert status["failed_count"] == 0
    assert status["total_count"] == 1
    assert status["pending_count"] == 1
    assert status["errors"] == {}
    assert status["current_item_id"] is None
