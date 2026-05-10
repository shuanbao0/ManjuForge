"""Tests for the async video + audio batch render tasks."""
import time
from types import SimpleNamespace

import pytest

from src.apps.comic_gen.models import (
    Character,
    GenerationStatus,
    ModelSettings,
    Script,
    StoryboardFrame,
    VideoTask,
)
from src.apps.comic_gen.pipeline import ComicGenPipeline


def _bare_pipeline(frames=None, characters=None):
    now = time.time()
    script = Script(
        id="proj1",
        title="t",
        original_text="",
        characters=characters or [],
        scenes=[],
        frames=frames or [],
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
    return p, script


# === Video predicate ======================================================


def test_video_predicate_skips_frame_without_image():
    f = StoryboardFrame(id="a", scene_id="s1")  # no image_url
    assert ComicGenPipeline._should_render_video(f) is False
    # Even force can't render without a source image.
    assert ComicGenPipeline._should_render_video(f, force=True) is False


def test_video_predicate_skips_already_rendered():
    f = StoryboardFrame(id="a", scene_id="s1", image_url="x.png", video_url="v.mp4")
    assert ComicGenPipeline._should_render_video(f) is False
    assert ComicGenPipeline._should_render_video(f, force=True) is True


def test_video_predicate_skips_when_selected_video_id_set():
    f = StoryboardFrame(
        id="a", scene_id="s1", image_url="x.png", selected_video_id="vt_123"
    )
    assert ComicGenPipeline._should_render_video(f) is False


def test_video_predicate_pending_frame_eligible():
    f = StoryboardFrame(id="a", scene_id="s1", image_url="x.png")
    assert ComicGenPipeline._should_render_video(f) is True


# === Video batch task =====================================================


def test_video_batch_task_counts_and_runs(monkeypatch):
    p, script = _bare_pipeline([
        StoryboardFrame(id="a", scene_id="s1", image_url="x.png"),  # pending
        StoryboardFrame(id="b", scene_id="s1"),                     # no image, skip
        StoryboardFrame(id="c", scene_id="s1", image_url="x.png", video_url="v.mp4"),  # done
    ])
    rendered = []
    p._render_single_video = lambda script, frame: rendered.append(frame.id)

    _, task_id = p.create_video_batch_render_task("proj1", force=False)
    assert p.asset_generation_tasks[task_id]["pending_count"] == 1
    p.process_video_batch_render_task(task_id)
    assert rendered == ["a"]
    assert p.asset_generation_tasks[task_id]["status"] == "completed"


def _frame_video_task(frame_id: str, task_id: str = "vt1", video_url: str = "v.mp4") -> VideoTask:
    return VideoTask(
        id=task_id,
        project_id="proj1",
        frame_id=frame_id,
        image_url="x.png",
        prompt="p",
        status="completed",
        video_url=video_url,
    )


def test_sync_frame_video_task_auto_selects_first_render():
    """First completed render for a pending frame becomes its selected variant
    so the UI's pending count drops without requiring a manual click."""
    p, script = _bare_pipeline([
        StoryboardFrame(id="a", scene_id="s1", image_url="x.png"),
    ])
    task = _frame_video_task("a", task_id="vt1", video_url="out/v1.mp4")

    p._sync_frame_video_task(script, task)

    frame = script.frames[0]
    assert frame.selected_video_id == "vt1"
    assert frame.video_url == "out/v1.mp4"
    # And the predicate flips to "no longer pending":
    assert ComicGenPipeline._should_render_video(frame) is False


def test_sync_frame_video_task_preserves_user_selection():
    """A second completed render must NOT silently override an existing
    selection — that selection might be the one the user picked."""
    p, script = _bare_pipeline([
        StoryboardFrame(
            id="a",
            scene_id="s1",
            image_url="x.png",
            selected_video_id="vt_user_choice",
            video_url="out/user.mp4",
        ),
    ])
    task = _frame_video_task("a", task_id="vt2", video_url="out/v2.mp4")

    p._sync_frame_video_task(script, task)

    frame = script.frames[0]
    assert frame.selected_video_id == "vt_user_choice"
    assert frame.video_url == "out/user.mp4"


def test_sync_frame_video_task_ignores_unknown_frame():
    """Tasks whose frame was deleted between submit and completion must not
    raise — just no-op."""
    p, script = _bare_pipeline([])
    task = _frame_video_task("ghost")
    p._sync_frame_video_task(script, task)  # must not raise


def test_video_batch_isolates_failure():
    p, _ = _bare_pipeline([
        StoryboardFrame(id="a", scene_id="s1", image_url="x.png"),
        StoryboardFrame(id="b", scene_id="s1", image_url="x.png"),
    ])
    p._render_single_video = lambda script, frame: (
        (_ for _ in ()).throw(RuntimeError("vendor 500")) if frame.id == "b" else None
    )
    _, task_id = p.create_video_batch_render_task("proj1")
    p.process_video_batch_render_task(task_id)
    task = p.asset_generation_tasks[task_id]
    assert task["completed_count"] == 1
    assert task["failed_count"] == 1
    assert "b" in task["errors"]


# === Audio predicate ======================================================


def test_audio_predicate_skips_frame_with_no_source_material():
    f = StoryboardFrame(id="a", scene_id="s1")  # no dialogue, no action
    assert ComicGenPipeline._should_render_audio(f) is False
    assert ComicGenPipeline._should_render_audio(f, force=True) is False


def test_audio_predicate_pending_when_dialogue_missing_audio():
    f = StoryboardFrame(id="a", scene_id="s1", dialogue="Hello!")
    assert ComicGenPipeline._should_render_audio(f) is True


def test_audio_predicate_pending_when_action_missing_sfx():
    f = StoryboardFrame(id="a", scene_id="s1", action_description="footsteps")
    assert ComicGenPipeline._should_render_audio(f) is True


def test_audio_predicate_skips_when_dialogue_already_synthesized():
    """Action description without sfx_url still keeps it pending; we only
    skip if BOTH outputs exist for their respective sources."""
    # Dialogue done, no action → not pending
    f = StoryboardFrame(id="a", scene_id="s1", dialogue="Hi", audio_url="a.mp3")
    assert ComicGenPipeline._should_render_audio(f) is False
    # Dialogue done, action present, sfx missing → pending
    f = StoryboardFrame(
        id="a", scene_id="s1", dialogue="Hi", audio_url="a.mp3",
        action_description="bang",
    )
    assert ComicGenPipeline._should_render_audio(f) is True


def test_audio_predicate_force_renders_anything_with_source():
    # Force re-renders even when both outputs are present, *if* there's source.
    f = StoryboardFrame(
        id="a", scene_id="s1", dialogue="Hi", audio_url="a.mp3",
        action_description="bang", sfx_url="s.mp3",
    )
    assert ComicGenPipeline._should_render_audio(f, force=True) is True
    # But no source → still false even with force.
    f2 = StoryboardFrame(id="b", scene_id="s1")
    assert ComicGenPipeline._should_render_audio(f2, force=True) is False


# === Audio batch task =====================================================


def test_audio_batch_task_counts_and_runs():
    p, _ = _bare_pipeline([
        StoryboardFrame(id="a", scene_id="s1", dialogue="hi"),                 # pending
        StoryboardFrame(id="b", scene_id="s1"),                                 # no source
        StoryboardFrame(id="c", scene_id="s1", dialogue="bye", audio_url="x"),  # done
    ])
    rendered = []
    p._render_single_audio = lambda script, frame: rendered.append(frame.id)

    _, task_id = p.create_audio_batch_render_task("proj1")
    assert p.asset_generation_tasks[task_id]["pending_count"] == 1
    p.process_audio_batch_render_task(task_id)
    assert rendered == ["a"]
