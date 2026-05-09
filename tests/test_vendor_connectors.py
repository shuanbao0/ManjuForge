"""Tests for the vendor connector registry (src/utils/vendor_connectors.py).

The connector list drives the Settings UI — pinning these invariants prevents
accidental drift between what the FE renders and what the credentials
allowlist accepts.
"""
from __future__ import annotations

import pytest

from src.auth.credentials import ALLOWED_KEYS
from src.utils.vendor_connectors import (
    DEFAULT_VENDOR_CONNECTORS,
    CredentialField,
    VendorConnector,
    VendorMode,
    VendorRegistry,
    get_default_vendor_registry,
)
from src.utils.provider_registry import get_default_provider_registry


# ── Registry façade ──────────────────────────────────────────────────────


def test_default_registry_lists_known_connectors():
    registry = get_default_vendor_registry()
    ids = {c.id for c in registry.all}
    for expected in ("dashscope", "kling", "vidu", "pixverse", "doubao", "hailuo"):
        assert expected in ids


def test_by_id_returns_match_or_none():
    registry = get_default_vendor_registry()
    assert registry.by_id("dashscope") is not None
    assert registry.by_id("does-not-exist") is None


def test_by_capability_filters_correctly():
    registry = get_default_vendor_registry()
    llm_connectors = registry.by_capability("llm")
    assert all("llm" in c.capabilities for c in llm_connectors)
    # DashScope is the only built-in LLM-capable connector for now.
    assert any(c.id == "dashscope" for c in llm_connectors)
    i2v = registry.by_capability("i2v")
    assert {c.id for c in i2v} >= {"kling", "vidu", "pixverse", "doubao", "hailuo"}


def test_by_capability_is_case_insensitive():
    registry = get_default_vendor_registry()
    assert registry.by_capability("I2V") == registry.by_capability("i2v")


def test_serialize_returns_connectors_with_required_fields():
    payload = get_default_vendor_registry().serialize()
    assert "connectors" in payload
    sample = payload["connectors"][0]
    for key in (
        "id",
        "display_name",
        "description",
        "capabilities",
        "common_fields",
        "modes",
        "mode_env_key",
        "family_prefixes",
        "docs_url",
        "badges",
        "accent",
    ):
        assert key in sample


def test_serialize_capability_filter_only_returns_matching_connectors():
    payload = get_default_vendor_registry().serialize(capability="i2v")
    assert all("i2v" in c["capabilities"] for c in payload["connectors"])
    assert all(c["id"] != "dashscope" or "i2v" in c["capabilities"] for c in payload["connectors"])


# ── Content invariants ──────────────────────────────────────────────────


def test_connector_ids_are_unique():
    ids = [c.id for c in DEFAULT_VENDOR_CONNECTORS]
    assert len(ids) == len(set(ids))


def test_dual_mode_connectors_declare_their_mode_env_key():
    for c in DEFAULT_VENDOR_CONNECTORS:
        if c.modes:
            assert c.mode_env_key, f"{c.id} has modes but no mode_env_key"


def test_every_credential_key_is_in_credentials_allowlist():
    """Legacy global-env vendors round-trip credentials through
    ``src.auth.credentials.ALLOWED_KEYS`` (the historical ``/config/env``
    path). Newer vendors store credentials only on the per-user
    ``ModelInstance`` row's encrypted blob and do NOT need to be in
    ``ALLOWED_KEYS`` — see CLAUDE.md "Settings is ModelInstance-driven"."""
    LEGACY_GLOBAL_ENV_VENDORS = frozenset(
        {"dashscope", "kling", "vidu", "pixverse", "doubao", "hailuo"}
    )
    leaked: list[str] = []
    for connector in DEFAULT_VENDOR_CONNECTORS:
        if connector.id not in LEGACY_GLOBAL_ENV_VENDORS:
            continue
        for f in connector.common_fields:
            if f.key not in ALLOWED_KEYS:
                leaked.append(f.key)
        for mode in connector.modes:
            for f in mode.fields:
                if f.key not in ALLOWED_KEYS:
                    leaked.append(f.key)
        if connector.mode_env_key and connector.mode_env_key not in ALLOWED_KEYS:
            leaked.append(connector.mode_env_key)
    assert not leaked, (
        f"legacy vendor connector keys missing from credentials allowlist: {leaked}"
    )


def test_connector_family_prefixes_resolve_in_provider_registry():
    """A connector advertising a family prefix must have at least one
    matching family in the provider routing registry — otherwise the
    runtime cannot dispatch to it."""
    pr = get_default_provider_registry()
    for connector in DEFAULT_VENDOR_CONNECTORS:
        for prefix in connector.family_prefixes:
            try:
                pr.get_family_config(prefix)
            except KeyError:  # pragma: no cover — only fires on regression
                pytest.fail(
                    f"connector {connector.id} declares family_prefix {prefix!r} "
                    f"but provider_registry has no family for it"
                )


def test_dashscope_connector_has_required_api_key_field():
    registry = get_default_vendor_registry()
    dashscope = registry.by_id("dashscope")
    assert dashscope is not None
    keys = {f.key for f in dashscope.common_fields}
    assert "DASHSCOPE_API_KEY" in keys


def test_modes_for_kling_have_dashscope_and_vendor():
    kling = get_default_vendor_registry().by_id("kling")
    assert kling is not None
    mode_ids = {m.id for m in kling.modes}
    assert mode_ids == {"dashscope", "vendor"}


def test_vendor_mode_required_keys_match_secret_field_definition():
    """Vendor-mode required fields for Kling should be access + secret keys."""
    kling = get_default_vendor_registry().by_id("kling")
    assert kling is not None
    vendor_mode = next((m for m in kling.modes if m.id == "vendor"), None)
    assert vendor_mode is not None
    secret_keys = {f.key for f in vendor_mode.fields if f.secret and f.required}
    assert {"KLING_ACCESS_KEY", "KLING_SECRET_KEY"} <= secret_keys


# ── Custom registry construction ─────────────────────────────────────────


def test_can_build_custom_registry():
    custom = VendorConnector(
        id="acme",
        display_name="Acme Vision",
        description="custom test connector",
        capabilities=("i2v",),
        common_fields=(CredentialField(key="ACME_API_KEY", label="API Key", secret=True),),
        modes=(
            VendorMode(id="dashscope", label="DashScope"),
            VendorMode(
                id="vendor",
                label="Vendor",
                fields=(CredentialField(key="ACME_VENDOR_KEY", label="Vendor Key", secret=True),),
            ),
        ),
        mode_env_key="ACME_PROVIDER_MODE",
    )
    registry = VendorRegistry([custom])
    assert registry.by_id("acme") is custom
    assert "ACME_API_KEY" in registry.all_credential_keys()
    assert "ACME_VENDOR_KEY" in registry.all_credential_keys()
    assert "ACME_PROVIDER_MODE" in registry.all_credential_keys()
