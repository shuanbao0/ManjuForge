"""Tests for the entity extraction package.

Covers the three concerns separately:

* ``MatchSpec`` rules (pure functions, no LLM).
* ``EntityCatalog`` Series-first vs script-fallback behaviour + dedup.
* ``IncrementalExtraction`` honouring ``match_id`` from the LLM and
  falling through to ``MatchSpec`` when the LLM forgets.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

import pytest

from src.apps.comic_gen.extraction import (
    CharacterMatchSpec,
    EntityCatalog,
    FullExtraction,
    IncrementalExtraction,
    PropMatchSpec,
    SceneMatchSpec,
    get_strategy,
    list_strategies,
)
from src.apps.comic_gen.models import Character, Prop, Scene, Script, Series


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_script(**kw) -> Script:
    now = time.time()
    return Script(
        id=kw.pop("id", str(uuid.uuid4())),
        title=kw.pop("title", "Ep1"),
        original_text=kw.pop("original_text", "..."),
        created_at=now,
        updated_at=now,
        **kw,
    )


def _make_series(**kw) -> Series:
    now = time.time()
    return Series(
        id=kw.pop("id", str(uuid.uuid4())),
        title=kw.pop("title", "S1"),
        created_at=now,
        updated_at=now,
        **kw,
    )


class FakeLLM:
    """Minimal stand-in for ScriptProcessor — only ``extract_entities``."""

    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload
        self.last_existing: Optional[Dict[str, Any]] = None

    @property
    def is_configured(self) -> bool:
        return True

    def extract_entities(self, text: str, existing=None) -> Dict[str, Any]:
        self.last_existing = existing
        return self._payload


# ── MatchSpec ─────────────────────────────────────────────────────────


def test_character_spec_matches_normalized_name():
    spec = CharacterMatchSpec()
    ch = Character(id="x", name="叶墨", description="...", gender="男")
    assert spec.is_same(ch, {"name": " 叶墨 ", "gender": "男"})


def test_character_spec_rejects_gender_conflict():
    spec = CharacterMatchSpec()
    ch = Character(id="x", name="Alex", description="...", gender="male")
    assert spec.is_same(ch, {"name": "Alex", "gender": "male"})
    assert not spec.is_same(ch, {"name": "Alex", "gender": "female"})


def test_character_spec_allows_unknown_gender():
    """Blank gender on either side should NOT block a match."""
    spec = CharacterMatchSpec()
    ch = Character(id="x", name="Alex", description="...", gender=None)
    assert spec.is_same(ch, {"name": "Alex", "gender": "male"})
    ch2 = Character(id="x", name="Alex", description="...", gender="male")
    assert spec.is_same(ch2, {"name": "Alex"})


def test_scene_spec_separates_by_time_of_day():
    spec = SceneMatchSpec()
    night = Scene(id="x", name="卧室", description="...", time_of_day="夜")
    assert not spec.is_same(night, {"name": "卧室", "time_of_day": "白天"})
    assert spec.is_same(night, {"name": "卧室", "time_of_day": "夜"})
    # Missing time on candidate should still match (don't fragment on nulls)
    assert spec.is_same(night, {"name": "卧室"})


def test_prop_spec_name_only():
    spec = PropMatchSpec()
    p = Prop(id="x", name="手机", description="...")
    assert spec.is_same(p, {"name": "手机"})
    assert not spec.is_same(p, {"name": "钱包"})


# ── EntityCatalog ─────────────────────────────────────────────────────


def test_catalog_writes_to_series_when_present():
    script = _make_script()
    series = _make_series()
    catalog = EntityCatalog(script, series)

    entity, created = catalog.upsert_character({"name": "叶墨", "gender": "男"})

    assert created is True
    assert entity.name == "叶墨"
    assert series.characters == [entity], "new character should land on Series"
    assert script.characters == [], "Script should stay clean when Series exists"


def test_catalog_falls_back_to_script_without_series():
    script = _make_script()
    catalog = EntityCatalog(script, series=None)

    entity, created = catalog.upsert_character({"name": "叶墨"})

    assert created is True
    assert script.characters == [entity]


def test_catalog_upsert_reuses_existing_match():
    series = _make_series(characters=[
        Character(id="existing", name="叶墨", description="hero", gender="男"),
    ])
    catalog = EntityCatalog(_make_script(), series)

    entity, created = catalog.upsert_character({"name": "叶墨", "gender": "男"})

    assert created is False
    assert entity.id == "existing"
    assert len(series.characters) == 1, "no duplicate should be appended"


def test_catalog_link_to_episode_is_idempotent():
    script = _make_script()
    catalog = EntityCatalog(script, _make_series())

    catalog.link_to_episode(character_ids=["a", "b"])
    catalog.link_to_episode(character_ids=["b", "c"])

    assert script.used_character_ids == ["a", "b", "c"]


def test_catalog_summary_omits_heavy_fields():
    """The LLM summary should be compact (no full descriptions)."""
    series = _make_series(characters=[
        Character(id="c1", name="叶墨", description="x" * 500, gender="男"),
    ])
    catalog = EntityCatalog(_make_script(), series)

    summary = catalog.summary_for_llm()

    char = summary["characters"][0]
    assert "description" not in char
    assert char == {"id": "c1", "name": "叶墨", "gender": "男", "age": None}


# ── Strategies + Registry ─────────────────────────────────────────────


def test_registry_returns_known_strategies():
    assert "full" in list_strategies()
    assert "incremental" in list_strategies()
    assert isinstance(get_strategy("full"), FullExtraction)
    assert isinstance(get_strategy("incremental"), IncrementalExtraction)


def test_registry_raises_on_unknown():
    with pytest.raises(ValueError, match="Unknown extraction strategy"):
        get_strategy("nonsense")


def test_full_strategy_ignores_catalog_summary():
    """FullExtraction must not pass ``existing`` to the LLM."""
    llm = FakeLLM({"characters": [{"name": "叶墨"}], "scenes": [], "props": []})
    catalog = EntityCatalog(_make_script(), _make_series())

    FullExtraction().extract("...", catalog, llm)

    assert llm.last_existing is None


def test_incremental_strategy_passes_catalog_to_llm():
    """IncrementalExtraction must feed the catalog summary to the LLM."""
    series = _make_series(characters=[
        Character(id="c1", name="叶墨", description="hero", gender="男"),
    ])
    llm = FakeLLM({"characters": [{"match_id": "c1", "name": "叶墨"}], "scenes": [], "props": []})
    catalog = EntityCatalog(_make_script(), series)

    IncrementalExtraction().extract("...", catalog, llm)

    assert llm.last_existing is not None
    assert llm.last_existing["characters"][0]["id"] == "c1"


def test_incremental_honours_llm_match_id():
    """When LLM returns match_id pointing at an existing entity, reuse it."""
    series = _make_series(characters=[
        Character(id="c1", name="叶墨", description="hero", gender="男"),
    ])
    llm = FakeLLM({
        "characters": [{"match_id": "c1", "name": "叶墨"}],
        "scenes": [],
        "props": [],
    })
    catalog = EntityCatalog(_make_script(), series)

    result = IncrementalExtraction().extract("...", catalog, llm)

    assert result.reused_character_ids == ["c1"]
    assert result.created_character_ids == []
    assert len(series.characters) == 1, "no new character should be appended"


def test_incremental_dedup_safety_net_catches_llm_miss():
    """Even when LLM omits match_id, the catalog's MatchSpec must catch
    a duplicate (same name + compatible gender)."""
    series = _make_series(characters=[
        Character(id="c1", name="叶墨", description="hero", gender="男"),
    ])
    llm = FakeLLM({
        # LLM forgot to set match_id — but spec should still match
        "characters": [{"name": "叶墨", "gender": "男"}],
        "scenes": [],
        "props": [],
    })
    catalog = EntityCatalog(_make_script(), series)

    result = IncrementalExtraction().extract("...", catalog, llm)

    assert result.reused_character_ids == ["c1"]
    assert len(series.characters) == 1


def test_incremental_creates_truly_new_entities():
    series = _make_series(characters=[
        Character(id="c1", name="叶墨", description="hero", gender="男"),
    ])
    llm = FakeLLM({
        "characters": [{"name": "陈雪", "gender": "女"}],
        "scenes": [{"name": "天台", "time_of_day": "夜"}],
        "props": [],
    })
    catalog = EntityCatalog(_make_script(), series)

    result = IncrementalExtraction().extract("...", catalog, llm)

    assert len(result.created_character_ids) == 1
    assert len(result.created_scene_ids) == 1
    assert len(series.characters) == 2
    assert len(series.scenes) == 1


def test_link_to_episode_after_extraction():
    """Script.used_*_ids should accumulate both created and reused entities."""
    series = _make_series(characters=[
        Character(id="c1", name="叶墨", description="...", gender="男"),
    ])
    llm = FakeLLM({
        "characters": [
            {"match_id": "c1", "name": "叶墨"},
            {"name": "陈雪", "gender": "女"},
        ],
        "scenes": [],
        "props": [],
    })
    script = _make_script()
    catalog = EntityCatalog(script, series)

    IncrementalExtraction().extract("...", catalog, llm)

    assert "c1" in script.used_character_ids
    assert len(script.used_character_ids) == 2
