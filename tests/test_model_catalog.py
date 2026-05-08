"""Tests for the model catalog registry (src/utils/model_catalog.py).

The catalog drives both backend provider routing and the frontend Settings
dropdowns. These tests pin the public surface so future contributors can add
``ModelCard`` entries without accidentally breaking the registry contract.
"""
from __future__ import annotations

import pytest

from src.utils.model_catalog import (
    ASPECT_RATIOS,
    I2I_CARDS,
    I2V_CARDS,
    LLM_PRESETS,
    LLMPreset,
    ModelCard,
    ModelCatalog,
    T2I_CARDS,
    get_default_catalog,
)
from src.utils.provider_registry import get_default_provider_registry


# ── ModelCatalog public API ──────────────────────────────────────────────


def test_default_catalog_has_cards_presets_and_aspect_ratios():
    catalog = get_default_catalog()
    assert len(catalog.cards) > 0
    assert len(catalog.presets) > 0
    assert len(catalog.aspect_ratios) > 0


def test_by_capability_filters_correctly():
    catalog = get_default_catalog()
    t2i = catalog.by_capability("t2i")
    assert all("t2i" in c.capabilities for c in t2i)
    # A card with multiple capabilities (e.g. wan2.6-i2v supports i2v + r2v + t2v)
    # should appear in all of its capability buckets.
    i2v_ids = {c.id for c in catalog.by_capability("i2v")}
    r2v_ids = {c.id for c in catalog.by_capability("r2v")}
    assert "wan2.6-i2v" in i2v_ids
    assert "wan2.6-i2v" in r2v_ids


def test_by_id_returns_match_or_none():
    catalog = get_default_catalog()
    card = catalog.by_id("wan2.6-i2v")
    assert card is not None and card.id == "wan2.6-i2v"
    assert catalog.by_id("does-not-exist") is None


def test_by_capability_is_case_insensitive():
    catalog = get_default_catalog()
    assert catalog.by_capability("T2I") == catalog.by_capability("t2i")


def test_serialize_includes_required_top_level_keys():
    payload = get_default_catalog().serialize()
    for key in ("cards", "presets", "aspect_ratios"):
        assert key in payload
    sample = payload["cards"][0]
    for key in ("id", "family", "display_name", "capabilities", "available", "badges"):
        assert key in sample


def test_serialize_capability_filter_only_returns_matching_cards():
    payload = get_default_catalog().serialize(capability="i2v")
    assert all("i2v" in card["capabilities"] for card in payload["cards"])


# ── Catalog content invariants ───────────────────────────────────────────


def test_t2i_cards_advertise_t2i_capability():
    for card in T2I_CARDS:
        assert "t2i" in card.capabilities


def test_i2v_cards_advertise_i2v_capability():
    for card in I2V_CARDS:
        assert "i2v" in card.capabilities


def test_card_ids_are_unique_across_catalog():
    all_ids = [c.id for c in (*T2I_CARDS, *I2I_CARDS, *I2V_CARDS)]
    assert len(all_ids) == len(set(all_ids))


def test_card_families_resolve_in_provider_registry():
    """Every card family must be routable by the provider registry, otherwise
    the FE would offer a model the backend can't dispatch."""
    registry = get_default_provider_registry()
    for card in (*T2I_CARDS, *I2I_CARDS, *I2V_CARDS):
        # Use the card id (not family) so the registry's longest-prefix match
        # exercises the same code path the runtime uses.
        try:
            registry.get_family_config(card.id)
        except KeyError as exc:  # pragma: no cover — surfaces missing family
            pytest.fail(f"card {card.id} (family={card.family}) missing in registry: {exc}")


def test_aspect_ratios_have_required_fields():
    for ratio in ASPECT_RATIOS:
        assert {"id", "name", "description"}.issubset(ratio.keys())


# ── LLM presets ──────────────────────────────────────────────────────────


def test_llm_presets_have_unique_ids():
    ids = [p.id for p in LLM_PRESETS]
    assert len(ids) == len(set(ids))


def test_llm_presets_have_at_least_one_recommendation():
    assert any("recommended" in p.badges for p in LLM_PRESETS)


def test_llm_presets_have_dashscope_default_with_no_base_url():
    dashscope = [p for p in LLM_PRESETS if p.provider == "dashscope"]
    assert len(dashscope) == 1
    assert dashscope[0].base_url == ""  # uses DashScope auto-detected endpoint


def test_llm_presets_openai_provider_entries_have_base_url():
    for preset in LLM_PRESETS:
        if preset.provider == "openai":
            assert preset.base_url, f"{preset.id} missing base_url"
            assert preset.suggested_models, f"{preset.id} missing suggested_models"


# ── Custom catalog construction ──────────────────────────────────────────


def test_can_build_custom_catalog_without_defaults():
    custom_card = ModelCard(
        id="acme-vid-1",
        family="acme-",
        display_name="Acme Video 1",
        capabilities=("i2v",),
    )
    custom_preset = LLMPreset(
        id="acme-llm",
        provider="openai",
        display_name="Acme LLM",
        base_url="https://api.acme.test/v1",
        suggested_models=("acme-1",),
    )
    catalog = ModelCatalog(cards=[custom_card], presets=[custom_preset])
    assert catalog.by_id("acme-vid-1") is custom_card
    assert catalog.preset_by_id("acme-llm") is custom_preset
    assert catalog.preset_by_id("missing") is None
