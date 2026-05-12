"""Tests for the novel→screenplay rewriter.

The actual rewrite quality is an LLM concern; these tests verify the
guardrails: configuration fallback, empty-input safety, pipeline
persistence, and the prompt format.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from src.apps.comic_gen.llm import ScriptProcessor
from src.apps.comic_gen.models import Script
from src.apps.comic_gen.pipeline import ComicGenPipeline


# ── ScriptProcessor.rewrite_to_screenplay ────────────────────────────


def test_rewrite_returns_empty_input_unchanged():
    sp = ScriptProcessor()
    assert sp.rewrite_to_screenplay("") == ""


def test_rewrite_returns_input_when_llm_unconfigured():
    sp = ScriptProcessor()
    with patch.object(sp, "llm") as fake_llm:
        fake_llm.is_configured = False
        assert sp.rewrite_to_screenplay("一段小说") == "一段小说"


def test_rewrite_returns_input_when_llm_raises():
    """LLM exception must not propagate — return original so the
    caller's downstream stages keep working."""
    sp = ScriptProcessor()
    with patch.object(sp, "llm") as fake_llm:
        fake_llm.is_configured = True
        fake_llm.chat.side_effect = RuntimeError("LLM down")
        assert sp.rewrite_to_screenplay("一段小说") == "一段小说"


def test_rewrite_strips_markdown_fences_if_model_wraps():
    """Defensive: some models wrap plain-text outputs in ```...```"""
    sp = ScriptProcessor()
    with patch.object(sp, "llm") as fake_llm:
        fake_llm.is_configured = True
        fake_llm.chat.return_value = "```\n1-1 卧室 [夜] [内]\n人物： 叶墨\n△ 叶墨翻身\n```"
        out = sp.rewrite_to_screenplay("一段小说")
    assert "```" not in out
    assert "1-1 卧室" in out


def test_rewrite_prompt_includes_format_constraints():
    """The system prompt must mention the wire-format markers
    (scene header / 人物 / △ / dialogue) so the LLM has a chance of
    emitting the exact format ``analyze_to_storyboard`` expects."""
    prompt = ScriptProcessor._build_screenplay_rewrite_prompt()
    assert "△" in prompt
    assert "人物：" in prompt
    assert "30-60 秒" in prompt
    assert "禁用镜头术语" in prompt


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


def _make_script(text: str = "一段小说原文") -> Script:
    now = time.time()
    return Script(
        id="p1", title="Ep1", original_text=text,
        created_at=now, updated_at=now,
    )


def test_pipeline_rewrite_persists_to_formatted_text(pipeline_fx):
    script = _make_script()
    pipeline_fx.scripts[script.id] = script
    pipeline_fx.script_processor.rewrite_to_screenplay.return_value = (
        "1-1 卧室 [夜] [内]\n人物： 叶墨\n△ 叶墨在床上翻身"
    )

    updated = pipeline_fx.rewrite_script_to_screenplay(script.id)

    assert updated.formatted_text.startswith("1-1 卧室")
    # original_text must remain intact for revert / re-rewrite
    assert updated.original_text == "一段小说原文"


def test_pipeline_rewrite_raises_when_no_text(pipeline_fx):
    script = _make_script(text="")
    pipeline_fx.scripts[script.id] = script

    with pytest.raises(ValueError, match="no original_text"):
        pipeline_fx.rewrite_script_to_screenplay(script.id)


def test_pipeline_rewrite_raises_on_unknown_script(pipeline_fx):
    with pytest.raises(ValueError, match="Script not found"):
        pipeline_fx.rewrite_script_to_screenplay("nonexistent")


def test_pipeline_rewrite_called_with_original_text(pipeline_fx):
    script = _make_script(text="原文 X")
    pipeline_fx.scripts[script.id] = script
    pipeline_fx.script_processor.rewrite_to_screenplay.return_value = "rewritten"

    pipeline_fx.rewrite_script_to_screenplay(script.id)

    pipeline_fx.script_processor.rewrite_to_screenplay.assert_called_once_with("原文 X")
