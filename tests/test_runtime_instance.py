"""Tests for the ``with_instance`` Context Manager + get_cred resolution."""
from __future__ import annotations

import pytest

from src.models.instance import InstanceType, ModelInstance
from src.runtime import current_instance, get_cred, with_instance


def _instance(creds: dict, **overrides) -> ModelInstance:
    base = dict(
        id="i1",
        user_id=1,
        instance_type=InstanceType.LLM,
        vendor_id="openai",
        model_name="gpt-5",
        display_name="t",
        credentials=creds,
    )
    base.update(overrides)
    return ModelInstance(**base)


def test_get_cred_falls_through_to_env_when_no_instance(monkeypatch):
    monkeypatch.setenv("FOO_KEY", "env-value")
    assert get_cred("FOO_KEY") == "env-value"


def test_with_instance_overrides_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-leaked")
    inst = _instance({"OPENAI_API_KEY": "instance-only"})
    with with_instance(inst):
        assert get_cred("OPENAI_API_KEY") == "instance-only"
    # Outside the scope, env wins again.
    assert get_cred("OPENAI_API_KEY") == "env-leaked"


def test_with_instance_falls_through_when_key_not_in_instance(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")
    inst = _instance({"OTHER_KEY": "x"})  # no OPENAI_API_KEY
    with with_instance(inst):
        # Instance has OTHER_KEY but not OPENAI_API_KEY → fall through to env.
        assert get_cred("OPENAI_API_KEY") == "from-env"
        assert get_cred("OTHER_KEY") == "x"


def test_with_instance_supports_none_as_noop():
    """Passing None is valid — useful for "use the global default" stages."""
    with with_instance(None) as bound:
        assert bound is None
        assert current_instance() is None


def test_with_instance_nests_and_restores():
    outer = _instance({"K": "outer"}, id="o")
    inner = _instance({"K": "inner"}, id="i")
    with with_instance(outer):
        assert get_cred("K") == "outer"
        with with_instance(inner):
            assert get_cred("K") == "inner"
            assert current_instance().id == "i"
        # After inner exits, outer is restored.
        assert get_cred("K") == "outer"
        assert current_instance().id == "o"
    assert current_instance() is None


def test_get_cred_default_when_unset():
    assert get_cred("NEVER_SET_KEY") == ""
    assert get_cred("NEVER_SET_KEY", "fallback") == "fallback"


def test_empty_string_credential_falls_through(monkeypatch):
    """Empty-string credential on instance shouldn't shadow env."""
    monkeypatch.setenv("API", "from-env")
    inst = _instance({"API": ""})
    with with_instance(inst):
        # Empty string is treated as "unset" so env wins.
        assert get_cred("API") == "from-env"
