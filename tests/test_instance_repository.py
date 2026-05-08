"""Tests for :class:`InstanceRepository` — CRUD + crypto + isolation."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.models.instance import InstanceType, ModelInstance
from src.models.instance_repository import InstanceRepository


# ── Fixtures (mirror the env isolation pattern in test_auth.py) ───────────


@pytest.fixture
def env_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / "home"
    home.mkdir()
    db_path = tmp_path / "db" / "manjuforge.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MANJU_FORGE_DB_PATH", str(db_path))
    monkeypatch.setenv("MANJU_FORGE_JWT_SECRET", "test-jwt-secret-" + tmp_path.name)
    monkeypatch.setenv("MANJU_FORGE_MASTER_KEY", "kZ2Hh7jfvJZbPq4_E1WZ9wQyOJ2aXt1kHUoQH9YwUqM=")

    from src.auth import db as auth_db
    auth_db.reset_for_tests()
    auth_db.get_engine()  # eager create
    yield
    auth_db.reset_for_tests()


@pytest.fixture
def repo_factory(env_isolated):
    from src.auth.db import session_scope

    def make(session):
        return InstanceRepository(session)

    return make, session_scope


def _make_user(session, email: str = "u1@example.com") -> int:
    from src.auth.models import User
    from src.auth.security import hash_password

    user = User(email=email, password_hash=hash_password("pw"))
    session.add(user)
    session.flush()
    return user.id


def _draft(user_id: int, **overrides) -> ModelInstance:
    base = dict(
        id=ModelInstance.new_id(),
        user_id=user_id,
        instance_type=InstanceType.LLM,
        vendor_id="openai",
        model_name="gpt-5",
        display_name="工作室主力",
        credentials={"OPENAI_API_KEY": "sk-test"},
        is_default=False,
    )
    base.update(overrides)
    return ModelInstance(**base)


# ── CRUD ─────────────────────────────────────────────────────────────────


def test_create_round_trip(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        created = repo.create(_draft(user_id))
        assert created.id
        assert created.credentials == {"OPENAI_API_KEY": "sk-test"}

        fetched = repo.get(created.id, user_id)
        assert fetched is not None
        assert fetched.display_name == "工作室主力"
        assert fetched.credentials == {"OPENAI_API_KEY": "sk-test"}


def test_credentials_are_encrypted_at_rest(repo_factory):
    """The raw DB blob must NOT contain the plaintext API key."""
    from src.auth.models import ModelInstanceRow

    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        created = repo.create(_draft(user_id, credentials={"OPENAI_API_KEY": "sk-MAGIC-12345"}))
        row = s.get(ModelInstanceRow, created.id)
        assert row is not None
        assert "sk-MAGIC-12345" not in row.encrypted_credentials


def test_list_for_user_filters_by_type(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        repo.create(_draft(user_id, instance_type=InstanceType.LLM, model_name="gpt-5"))
        repo.create(_draft(user_id, instance_type=InstanceType.T2I, model_name="wan2.6-t2i"))
        all_ = repo.list_for_user(user_id)
        assert len(all_) == 2
        llms = repo.list_for_user(user_id, instance_type=InstanceType.LLM)
        assert len(llms) == 1
        assert llms[0].instance_type == InstanceType.LLM


def test_users_cannot_see_each_others_instances(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        u1 = _make_user(s, email="u1@example.com")
        u2 = _make_user(s, email="u2@example.com")
        repo = make(s)
        secret = repo.create(_draft(u1, display_name="u1-secret"))
        # u2 cannot read u1's instance even by id.
        assert repo.get(secret.id, u2) is None
        assert all(i.user_id == u2 for i in repo.list_for_user(u2))


def test_update_overwrites_only_provided_fields(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        inst = repo.create(_draft(user_id, display_name="old", base_url="http://old"))
        updated = repo.update(
            inst.id, user_id, display_name="new", base_url="http://new"
        )
        assert updated is not None
        assert updated.display_name == "new"
        assert updated.base_url == "http://new"
        # model_name and credentials untouched
        assert updated.model_name == inst.model_name
        assert updated.credentials == inst.credentials


def test_delete_removes_instance(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        inst = repo.create(_draft(user_id))
        assert repo.delete(inst.id, user_id) is True
        assert repo.get(inst.id, user_id) is None
        assert repo.delete(inst.id, user_id) is False


def test_delete_refuses_other_users_instance(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        u1 = _make_user(s, "u1@example.com")
        u2 = _make_user(s, "u2@example.com")
        repo = make(s)
        inst = repo.create(_draft(u1))
        assert repo.delete(inst.id, u2) is False
        assert repo.get(inst.id, u1) is not None


# ── Default invariant ────────────────────────────────────────────────────


def test_set_default_demotes_previous_default(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        a = repo.create(_draft(user_id, model_name="gpt-5", is_default=True))
        b = repo.create(_draft(user_id, model_name="claude-opus-4-7", is_default=False))
        assert a.is_default and not b.is_default

        # Promote b → a should drop to non-default.
        repo.set_default(b.id, user_id)
        re_a = repo.get(a.id, user_id)
        re_b = repo.get(b.id, user_id)
        assert re_a is not None and re_b is not None
        assert re_b.is_default is True
        assert re_a.is_default is False


def test_default_is_scoped_per_type(repo_factory):
    """Each instance_type can have its own default; promoting an LLM doesn't
    touch the T2I default."""
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        llm_default = repo.create(
            _draft(user_id, instance_type=InstanceType.LLM, model_name="gpt-5", is_default=True)
        )
        t2i_default = repo.create(
            _draft(user_id, instance_type=InstanceType.T2I, model_name="wan2.6-t2i", is_default=True)
        )
        # New LLM, set as default.
        new_llm = repo.create(
            _draft(user_id, instance_type=InstanceType.LLM, model_name="claude-opus-4-7")
        )
        repo.set_default(new_llm.id, user_id)
        # T2I default should be untouched.
        assert repo.get(t2i_default.id, user_id).is_default is True
        # LLM default flipped.
        assert repo.get(llm_default.id, user_id).is_default is False
        assert repo.get(new_llm.id, user_id).is_default is True


def test_get_default_returns_marked_instance(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        repo.create(_draft(user_id, model_name="gpt-5", is_default=False))
        b = repo.create(_draft(user_id, model_name="claude-opus-4-7", is_default=True))
        default = repo.get_default(user_id, InstanceType.LLM)
        assert default is not None
        assert default.id == b.id


def test_get_default_returns_none_when_unset(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        repo.create(_draft(user_id, is_default=False))
        assert repo.get_default(user_id, InstanceType.LLM) is None


# ── Validation ───────────────────────────────────────────────────────────


def test_create_rejects_missing_required_fields(repo_factory):
    make, scope = repo_factory
    with scope() as s:
        user_id = _make_user(s)
        repo = make(s)
        with pytest.raises(ValueError):
            repo.create(_draft(user_id, display_name=""))
        with pytest.raises(ValueError):
            repo.create(_draft(user_id, model_name=""))
        with pytest.raises(ValueError):
            repo.create(_draft(user_id, vendor_id=""))
