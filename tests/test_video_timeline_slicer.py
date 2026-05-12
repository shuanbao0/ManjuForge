"""Tests for ``ScriptProcessor.slice_video_prompt_timeline`` and the
pipeline wrapper that drives it.

The slicer is LLM-driven, so tests target:

* The pure window-segmentation helper (``_segment_windows``).
* The deterministic mock fallback path used when no LLM is configured.
* The pipeline method's frame-resolution + persistence behaviour.
"""
from __future__ import annotations

import time
import uuid
from unittest.mock import patch

import pytest

from src.apps.comic_gen.llm import ScriptProcessor
from src.apps.comic_gen.models import (
    Character,
    Scene,
    Script,
    StoryboardFrame,
    VideoTask,
)
from src.apps.comic_gen.pipeline import ComicGenPipeline


# ── Window segmentation ──────────────────────────────────────────────


def test_segment_windows_exact_multiple():
    assert ScriptProcessor._segment_windows(6, 3) == [(0, 3), (3, 6)]


def test_segment_windows_short_tail():
    """Last window must shrink so the total equals duration exactly."""
    assert ScriptProcessor._segment_windows(7, 3) == [(0, 3), (3, 6), (6, 7)]


def test_segment_windows_under_one_segment():
    assert ScriptProcessor._segment_windows(2, 3) == [(0, 2)]


def test_segment_windows_zero_duration():
    assert ScriptProcessor._segment_windows(0, 3) == []


# ── Mock slicer (no LLM configured path) ─────────────────────────────


def test_mock_slice_returns_window_skeleton():
    out = ScriptProcessor._mock_slice_video_prompt_timeline(
        "叶墨翻身", duration_s=6, segment_seconds=3,
        location="卧室", characters=["叶墨"], sound="手机震动声",
    )
    assert "<location>卧室</location>" in out
    assert "<role>叶墨</role>" in out
    assert "<sound>手机震动声</sound>" in out
    assert "<n0-3>" in out and "</n0-3>" in out
    assert "<n3-6>" in out and "</n3-6>" in out


def test_mock_slice_no_meta_omits_tags():
    """No location/characters/sound → no meta block."""
    out = ScriptProcessor._mock_slice_video_prompt_timeline(
        "叶墨翻身", duration_s=3, segment_seconds=3,
        location=None, characters=None, sound=None,
    )
    assert "<location>" not in out
    assert "<role>" not in out
    assert "<n0-3>叶墨翻身</n0-3>" in out


# ── slice_video_prompt_timeline public entry ──────────────────────────


def test_slice_returns_input_when_prompt_empty():
    sp = ScriptProcessor()
    assert sp.slice_video_prompt_timeline("", duration_s=5) == ""


def test_slice_returns_input_when_duration_zero():
    sp = ScriptProcessor()
    assert sp.slice_video_prompt_timeline("anything", duration_s=0) == "anything"


def test_slice_falls_back_to_mock_when_unconfigured():
    """When LLM isn't configured, the public method delegates to mock fallback."""
    sp = ScriptProcessor()
    # ScriptProcessor.is_configured reads from llm.is_configured — patch the
    # adapter to look unconfigured for this test.
    with patch.object(sp, "llm") as fake_llm:
        fake_llm.is_configured = False
        out = sp.slice_video_prompt_timeline(
            "叶墨翻身", duration_s=3, location="卧室",
        )
    assert "<n0-3>" in out
    assert "<location>卧室</location>" in out


def test_slice_returns_original_when_llm_output_missing_tags():
    """Bad LLM output (no <n...> tag) must not corrupt the timeline field."""
    sp = ScriptProcessor()
    with patch.object(sp, "llm") as fake_llm:
        fake_llm.is_configured = True
        fake_llm.chat.return_value = "this is not a valid timeline"
        out = sp.slice_video_prompt_timeline("original prompt", duration_s=3)
    assert out == "original prompt"


# ── Pipeline wrapper ─────────────────────────────────────────────────


@pytest.fixture
def pipeline_fx(tmp_path):
    with patch("src.apps.comic_gen.pipeline.ScriptProcessor"), \
         patch("src.apps.comic_gen.pipeline.AssetGenerator"), \
         patch("src.apps.comic_gen.pipeline.StoryboardGenerator"), \
         patch("src.apps.comic_gen.pipeline.VideoGenerator"), \
         patch("src.apps.comic_gen.pipeline.AudioGenerator"), \
         patch("src.apps.comic_gen.pipeline.ExportManager"):
        p = ComicGenPipeline()
    p.data_file = str(tmp_path / "projects.json")
    p.series_data_file = str(tmp_path / "series.json")
    p.scripts = {}
    p.series_store = {}
    return p


def _make_script_with_frame(duration: int = 5) -> Script:
    now = time.time()
    char = Character(id="c1", name="叶墨", description="...", gender="男")
    scene = Scene(id="s1", name="卧室", description="...", time_of_day="夜")
    frame = StoryboardFrame(
        id="f1", scene_id="s1", character_ids=["c1"],
        action_description="叶墨翻身", video_prompt="叶墨在床上翻身",
        sfx_prompt="手机震动声",
    )
    task = VideoTask(
        id="vt1", project_id="p1", frame_id="f1",
        image_url="x.png", prompt="...", duration=duration,
    )
    return Script(
        id="p1", title="Ep1", original_text="...",
        characters=[char], scenes=[scene], frames=[frame], video_tasks=[task],
        created_at=now, updated_at=now,
    )


def test_pipeline_slice_persists_timeline(pipeline_fx):
    script = _make_script_with_frame(duration=6)
    pipeline_fx.scripts[script.id] = script
    # Stub the slicer to return a fixed value so the test asserts on
    # *write-through* behaviour rather than slicer output.
    pipeline_fx.script_processor.slice_video_prompt_timeline.return_value = (
        "<location>卧室</location><role>叶墨</role>\n<n0-3>...</n0-3>\n<n3-6>...</n3-6>"
    )

    frame = pipeline_fx.slice_frame_video_timeline(script.id, "f1")

    assert frame.video_prompt_timeline.startswith("<location>卧室</location>")
    # video_prompt itself must stay untouched
    assert frame.video_prompt == "叶墨在床上翻身"


def test_pipeline_slice_uses_video_task_duration(pipeline_fx):
    script = _make_script_with_frame(duration=9)
    pipeline_fx.scripts[script.id] = script
    pipeline_fx.script_processor.slice_video_prompt_timeline.return_value = "<n0-9>x</n0-9>"

    pipeline_fx.slice_frame_video_timeline(script.id, "f1")

    call_kwargs = pipeline_fx.script_processor.slice_video_prompt_timeline.call_args
    args, kwargs = call_kwargs
    # second positional arg is duration_s
    assert args[1] == 9


def test_pipeline_slice_respects_duration_override(pipeline_fx):
    script = _make_script_with_frame(duration=9)
    pipeline_fx.scripts[script.id] = script
    pipeline_fx.script_processor.slice_video_prompt_timeline.return_value = "<n0-4>x</n0-4>"

    pipeline_fx.slice_frame_video_timeline(script.id, "f1", duration_override=4)

    args, _ = pipeline_fx.script_processor.slice_video_prompt_timeline.call_args
    assert args[1] == 4


def test_pipeline_slice_raises_when_video_prompt_missing(pipeline_fx):
    script = _make_script_with_frame()
    script.frames[0].video_prompt = None
    pipeline_fx.scripts[script.id] = script

    with pytest.raises(ValueError, match="no video_prompt"):
        pipeline_fx.slice_frame_video_timeline(script.id, "f1")


def test_pipeline_slice_raises_on_unknown_frame(pipeline_fx):
    script = _make_script_with_frame()
    pipeline_fx.scripts[script.id] = script

    with pytest.raises(ValueError, match="not found"):
        pipeline_fx.slice_frame_video_timeline(script.id, "nonexistent")
