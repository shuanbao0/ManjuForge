"""Tests for the voice-assignment chain.

Verifies each rule's contract in isolation, then the chain's
short-circuit + collision-avoidance behaviour end-to-end.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

import pytest

from src.apps.comic_gen.models import Character, Series
from src.apps.comic_gen.voice import (
    AssignContext,
    DefaultPoolRule,
    LLMMatchRule,
    LockedRule,
    SeriesReuseRule,
    VoiceAssigner,
)


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_char(name="叶墨", gender="男", **kw) -> Character:
    return Character(
        id=kw.pop("id", str(uuid.uuid4())),
        name=name,
        description=kw.pop("description", "..."),
        gender=gender,
        **kw,
    )


def _voices() -> List[Dict[str, Any]]:
    return [
        {"id": "voice_male_1", "name": "龙诚", "gender": "Male"},
        {"id": "voice_male_2", "name": "龙书", "gender": "Male"},
        {"id": "voice_female_1", "name": "龙小淳", "gender": "Female"},
        {"id": "voice_female_2", "name": "龙悦", "gender": "Female"},
    ]


# ── LockedRule ────────────────────────────────────────────────────────


def test_locked_rule_returns_existing_voice_id():
    ch = _make_char(voice_id="voice_male_1")
    assert LockedRule().try_assign(ch, _voices(), set(), AssignContext()) == "voice_male_1"


def test_locked_rule_falls_through_when_blank():
    ch = _make_char(voice_id=None)
    assert LockedRule().try_assign(ch, _voices(), set(), AssignContext()) is None


def test_locked_character_with_blank_voice_skips_chain():
    """Locked + blank voice means "do not auto-assign" — chain returns None."""
    ch = _make_char(voice_id=None, locked=True)
    assert LockedRule().try_assign(ch, _voices(), set(), AssignContext()) is None


# ── SeriesReuseRule ───────────────────────────────────────────────────


def test_series_reuse_picks_same_named_character_voice():
    """Same character name across episodes should reuse the same voice."""
    series_char = _make_char(name="叶墨", voice_id="voice_male_1")
    series = Series(
        id="s1", title="S1", characters=[series_char],
        created_at=time.time(), updated_at=time.time(),
    )
    ep_char = _make_char(name="叶墨")  # different id, same name
    ctx = AssignContext(series=series)

    assert SeriesReuseRule().try_assign(ep_char, _voices(), set(), ctx) == "voice_male_1"


def test_series_reuse_returns_none_without_series():
    ch = _make_char(name="叶墨")
    assert SeriesReuseRule().try_assign(ch, _voices(), set(), AssignContext()) is None


def test_series_reuse_skips_self():
    """A character matching itself in the series should not loop back."""
    ch = _make_char(name="叶墨", id="c1", voice_id=None)
    series = Series(
        id="s1", title="S1", characters=[ch],  # same id
        created_at=time.time(), updated_at=time.time(),
    )
    assert SeriesReuseRule().try_assign(ch, _voices(), set(), AssignContext(series=series)) is None


# ── LLMMatchRule ──────────────────────────────────────────────────────


class FakeLLM:
    def __init__(self, picked: Optional[str], should_raise: bool = False):
        self._picked = picked
        self._raise = should_raise
        self.calls = 0

    @property
    def is_configured(self) -> bool:
        return True

    def match_voice_for_character(self, character, candidates):
        self.calls += 1
        if self._raise:
            raise RuntimeError("LLM down")
        return self._picked


def test_llm_match_filters_by_gender_and_used():
    """LLMMatchRule must only show the LLM gender-compatible, unused voices."""
    captured: Dict[str, Any] = {}

    class CapturingLLM(FakeLLM):
        def match_voice_for_character(self, character, candidates):
            captured["candidates"] = candidates
            return candidates[0]["id"]

    rule = LLMMatchRule(CapturingLLM(picked=None))
    rule.try_assign(_make_char(gender="男"), _voices(), {"voice_male_1"}, AssignContext())

    ids = [c["id"] for c in captured["candidates"]]
    assert "voice_male_1" not in ids, "used voice should be filtered out"
    assert "voice_female_1" not in ids, "wrong-gender voice should be filtered out"
    assert "voice_male_2" in ids


def test_llm_match_returns_none_on_exception():
    rule = LLMMatchRule(FakeLLM(picked=None, should_raise=True))
    result = rule.try_assign(_make_char(), _voices(), set(), AssignContext())
    assert result is None


def test_llm_match_skips_when_unconfigured():
    class Unconfigured(FakeLLM):
        @property
        def is_configured(self):
            return False

    rule = LLMMatchRule(Unconfigured(picked=None))
    assert rule.try_assign(_make_char(), _voices(), set(), AssignContext()) is None


# ── DefaultPoolRule ───────────────────────────────────────────────────


def test_default_pool_picks_first_unused_gender_match():
    rule = DefaultPoolRule()
    ch = _make_char(gender="男")
    result = rule.try_assign(ch, _voices(), set(), AssignContext())
    assert result == "voice_male_1"


def test_default_pool_avoids_used_voices():
    rule = DefaultPoolRule()
    ch = _make_char(gender="男")
    result = rule.try_assign(ch, _voices(), {"voice_male_1"}, AssignContext())
    assert result == "voice_male_2"


def test_default_pool_reuses_when_all_taken():
    """When more characters than voices, the rule must not return None."""
    rule = DefaultPoolRule()
    ch = _make_char(gender="男")
    used = {"voice_male_1", "voice_male_2"}
    result = rule.try_assign(ch, _voices(), used, AssignContext())
    assert result in {"voice_male_1", "voice_male_2"}


# ── VoiceAssigner end-to-end ──────────────────────────────────────────


def test_assigner_chain_short_circuits():
    """First non-None rule wins."""
    locked_char = _make_char(name="A", voice_id="voice_male_1")
    blank_char = _make_char(name="B", gender="女")

    assigner = VoiceAssigner([LockedRule(), DefaultPoolRule()])
    mapping = assigner.assign_all(
        [locked_char, blank_char], _voices(), AssignContext()
    )

    assert mapping[locked_char.id] == "voice_male_1"
    assert mapping[blank_char.id] == "voice_female_1"


def test_assigner_marks_voices_used_across_characters():
    """Two unassigned same-gender characters should not collide."""
    a = _make_char(name="A", gender="男")
    b = _make_char(name="B", gender="男")

    assigner = VoiceAssigner([DefaultPoolRule()])
    mapping = assigner.assign_all([a, b], _voices(), AssignContext())

    assert mapping[a.id] != mapping[b.id]


def test_assigner_seeds_used_set_from_existing_voice_ids():
    """A character with a pre-set voice should pre-occupy that slot for others."""
    pinned = _make_char(name="A", gender="男", voice_id="voice_male_1")
    fresh = _make_char(name="B", gender="男")

    assigner = VoiceAssigner([LockedRule(), DefaultPoolRule()])
    mapping = assigner.assign_all([pinned, fresh], _voices(), AssignContext())

    assert mapping[fresh.id] == "voice_male_2", "must avoid the pinned voice"


def test_full_chain_prefers_series_reuse_over_llm():
    """Demonstrate canonical chain ordering."""
    series = Series(
        id="s1", title="S1",
        characters=[_make_char(name="叶墨", id="other_ep", voice_id="voice_male_1")],
        created_at=time.time(), updated_at=time.time(),
    )
    ch = _make_char(name="叶墨")

    llm = FakeLLM(picked="voice_male_2")  # would pick something else
    assigner = VoiceAssigner([
        LockedRule(), SeriesReuseRule(), LLMMatchRule(llm), DefaultPoolRule(),
    ])
    mapping = assigner.assign_all([ch], _voices(), AssignContext(series=series))

    assert mapping[ch.id] == "voice_male_1", "SeriesReuseRule should win over LLM"
    assert llm.calls == 0, "LLM should not be called when SeriesReuseRule matched"
