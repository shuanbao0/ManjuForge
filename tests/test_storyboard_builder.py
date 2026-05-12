"""Tests for ``StoryboardPromptBuilder``.

The builder is pure — no network, no LLM — so assertions can target
substring containment and the rendered example JSON without mocks.
"""
from __future__ import annotations

import json
import re

import pytest

from src.apps.comic_gen.prompts import StoryboardPromptBuilder


SAMPLE_ENTITIES = {
    "characters": [{"id": "c1", "name": "叶墨"}],
    "scenes": [{"id": "s1", "name": "卧室"}],
    "props": [{"id": "p1", "name": "手机"}],
}


# ── Minimal build ────────────────────────────────────────────────────


def test_build_with_no_blocks_just_renders_format_and_text():
    out = StoryboardPromptBuilder().build("剧本内容X")

    assert "剧本内容X" in out
    assert "# 输出格式" in out
    assert "# 角色" not in out, "role block must be opt-in"


# ── Block opt-in ─────────────────────────────────────────────────────


def test_role_block_opt_in():
    out = StoryboardPromptBuilder().with_role().build("...")
    assert "电影级的分镜师" in out


def test_visual_atoms_block_opt_in():
    out = StoryboardPromptBuilder().with_visual_atoms().build("...")
    assert "VISUAL ATOMIZATION" in out


def test_audio_atoms_block_only_when_requested():
    no_audio = StoryboardPromptBuilder().with_visual_atoms().build("...")
    assert "bgm_prompt" not in no_audio

    with_audio = StoryboardPromptBuilder().with_visual_atoms().with_audio_atoms().build("...")
    assert "bgm_prompt" in with_audio
    assert "sfx_prompt" in with_audio
    assert "AUDIO ATOMS" in with_audio


def test_entities_block_serialises_catalog():
    out = StoryboardPromptBuilder().with_entities(SAMPLE_ENTITIES).build("...")
    assert "已提取的实体上下文" in out
    assert "叶墨" in out
    assert "卧室" in out
    assert "手机" in out


def test_entities_block_handles_none_payload():
    """Builder must not crash when called with empty/None entities."""
    out = StoryboardPromptBuilder().with_entities(None).build("...")
    # Should still emit the block headers with empty arrays
    assert "Characters:" in out


# ── Example JSON shape ───────────────────────────────────────────────


def _extract_example_json(prompt: str) -> dict:
    """Pull the example JSON out of the rendered prompt."""
    # The example follows the "# 输出格式" header. Find the first
    # balanced {...} after it.
    marker = "# 输出格式"
    idx = prompt.find(marker)
    assert idx >= 0
    tail = prompt[idx:]
    start = tail.find("{")
    # Naive balanced-brace scan — works because the example is the only JSON.
    depth = 0
    for i, ch in enumerate(tail[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(tail[start : i + 1])
    raise AssertionError("Example JSON not found in prompt")


def test_example_shape_grows_with_audio_atoms():
    base = _extract_example_json(StoryboardPromptBuilder().with_visual_atoms().build("..."))
    assert "bgm_prompt" not in base["frames"][0]

    with_audio = _extract_example_json(
        StoryboardPromptBuilder().with_visual_atoms().with_audio_atoms().build("...")
    )
    for frame in with_audio["frames"]:
        assert "bgm_prompt" in frame
        assert "sfx_prompt" in frame


def test_builder_call_order_does_not_matter():
    """Same set of with_* calls must render identical output regardless of order."""
    a = (StoryboardPromptBuilder()
         .with_role().with_audio_atoms().with_visual_atoms()
         .with_entities(SAMPLE_ENTITIES).with_script_format()
         .build("剧本"))
    b = (StoryboardPromptBuilder()
         .with_script_format().with_entities(SAMPLE_ENTITIES)
         .with_visual_atoms().with_role().with_audio_atoms()
         .build("剧本"))
    assert a == b


def test_repeated_calls_are_idempotent():
    once = StoryboardPromptBuilder().with_visual_atoms().build("剧本")
    twice = (StoryboardPromptBuilder()
             .with_visual_atoms().with_visual_atoms().build("剧本"))
    assert once == twice
