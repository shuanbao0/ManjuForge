"""Tests for the new ``StoryboardFrame.title`` and ``duration_seconds``
fields and the pipeline's defensive parsing of LLM output.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src.apps.comic_gen.models import Scene, Script, StoryboardFrame
from src.apps.comic_gen.pipeline import ComicGenPipeline


# ── Model defaults ────────────────────────────────────────────────────


def test_frame_metadata_defaults_to_none():
    """Both fields are Optional — older project.json with no values
    must deserialize cleanly."""
    f = StoryboardFrame(id="x", scene_id="s")
    assert f.title is None
    assert f.duration_seconds is None


def test_duration_seconds_rejects_out_of_range():
    """Pydantic ge/le guards keep bad LLM output out of the model."""
    with pytest.raises(ValueError):
        StoryboardFrame(id="x", scene_id="s", duration_seconds=0)
    with pytest.raises(ValueError):
        StoryboardFrame(id="x", scene_id="s", duration_seconds=999)


# ── Pipeline defensive parsing ───────────────────────────────────────


@pytest.fixture
def pipeline_fx(tmp_path):
    with patch("src.apps.comic_gen.pipeline.ScriptProcessor"), \
         patch("src.apps.comic_gen.pipeline.AssetGenerator"), \
         patch("src.apps.comic_gen.pipeline.StoryboardGenerator"), \
         patch("src.apps.comic_gen.pipeline.VideoGenerator"), \
         patch("src.apps.comic_gen.pipeline.AudioGenerator"), \
         patch("src.apps.comic_gen.pipeline.ExportManager"):
        p = ComicGenPipeline()
    p.data_root = str(tmp_path)
    p.data_file = str(tmp_path / "projects.json")
    p.series_data_file = str(tmp_path / "series.json")
    p.scripts = {}
    p.series_store = {}
    return p


def _make_script_with_scene() -> Script:
    now = time.time()
    return Script(
        id="p1", title="Ep", original_text="...",
        scenes=[Scene(id="s1", name="卧室", description="...")],
        created_at=now, updated_at=now,
    )


def _stub_raw_frames(pipeline_fx, frames):
    pipeline_fx.script_processor.analyze_to_storyboard.return_value = frames
    pipeline_fx.resolve_episode_assets = lambda script: {
        "characters": script.characters,
        "scenes": script.scenes,
        "props": script.props,
    }


def test_analyze_picks_up_title_and_duration(pipeline_fx):
    """LLM-provided title + duration must land on the StoryboardFrame."""
    script = _make_script_with_scene()
    pipeline_fx.scripts[script.id] = script
    _stub_raw_frames(pipeline_fx, [
        {
            "scene_ref_name": "卧室", "character_ref_names": [], "prop_ref_names": [],
            "title": "震动惊醒", "duration_seconds": 4,
            "action_description": "翻身",
        }
    ])

    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = None
        scoped.return_value.__exit__.return_value = False
        updated = pipeline_fx.analyze_text_to_frames(script.id, "剧本")

    assert updated.frames[0].title == "震动惊醒"
    assert updated.frames[0].duration_seconds == 4


def test_analyze_coerces_string_duration(pipeline_fx):
    """Some LLMs return '4' or '4.0' — pipeline must coerce, not crash."""
    script = _make_script_with_scene()
    pipeline_fx.scripts[script.id] = script
    _stub_raw_frames(pipeline_fx, [
        {
            "scene_ref_name": "卧室", "character_ref_names": [], "prop_ref_names": [],
            "title": "test", "duration_seconds": "4.0",
            "action_description": "x",
        }
    ])

    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = None
        scoped.return_value.__exit__.return_value = False
        updated = pipeline_fx.analyze_text_to_frames(script.id, "...")

    assert updated.frames[0].duration_seconds == 4


def test_analyze_clamps_oversize_duration(pipeline_fx):
    """LLM emitting 9999 must be clamped to the model's 60s ceiling, not crash."""
    script = _make_script_with_scene()
    pipeline_fx.scripts[script.id] = script
    _stub_raw_frames(pipeline_fx, [
        {
            "scene_ref_name": "卧室", "character_ref_names": [], "prop_ref_names": [],
            "title": "test", "duration_seconds": 9999,
            "action_description": "x",
        }
    ])

    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = None
        scoped.return_value.__exit__.return_value = False
        updated = pipeline_fx.analyze_text_to_frames(script.id, "...")

    assert updated.frames[0].duration_seconds == 60


def test_analyze_handles_missing_metadata(pipeline_fx):
    """Old LLM responses without title/duration must still produce valid frames."""
    script = _make_script_with_scene()
    pipeline_fx.scripts[script.id] = script
    _stub_raw_frames(pipeline_fx, [
        {
            "scene_ref_name": "卧室", "character_ref_names": [], "prop_ref_names": [],
            "action_description": "x",
            # title and duration_seconds intentionally omitted
        }
    ])

    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = None
        scoped.return_value.__exit__.return_value = False
        updated = pipeline_fx.analyze_text_to_frames(script.id, "...")

    assert updated.frames[0].title is None
    assert updated.frames[0].duration_seconds is None


def test_analyze_normalises_empty_title_to_none(pipeline_fx):
    """Empty-string title is meaningless for UI — store as None."""
    script = _make_script_with_scene()
    pipeline_fx.scripts[script.id] = script
    _stub_raw_frames(pipeline_fx, [
        {
            "scene_ref_name": "卧室", "character_ref_names": [], "prop_ref_names": [],
            "title": "", "action_description": "x",
        }
    ])

    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = None
        scoped.return_value.__exit__.return_value = False
        updated = pipeline_fx.analyze_text_to_frames(script.id, "...")

    assert updated.frames[0].title is None


def test_analyze_handles_garbage_duration(pipeline_fx):
    """LLM returning 'four' shouldn't break the frame — duration_seconds=None."""
    script = _make_script_with_scene()
    pipeline_fx.scripts[script.id] = script
    _stub_raw_frames(pipeline_fx, [
        {
            "scene_ref_name": "卧室", "character_ref_names": [], "prop_ref_names": [],
            "title": "x", "duration_seconds": "four",
            "action_description": "x",
        }
    ])

    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = None
        scoped.return_value.__exit__.return_value = False
        updated = pipeline_fx.analyze_text_to_frames(script.id, "...")

    assert updated.frames[0].duration_seconds is None
