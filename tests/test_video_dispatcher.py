"""Tests for the video dispatcher (src/models/video_dispatcher.py)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.models.video_dispatcher import (
    KlingVendorAdapter,
    VideoAdapter,
    VideoGenerationContext,
    VideoModelDispatcher,
    ViduVendorAdapter,
    WanxDashScopeAdapter,
    build_default_dispatcher,
)


class _FakeAdapter(VideoAdapter):
    def __init__(self, label: str):
        self.label = label
        self.calls = []

    def generate(self, ctx: VideoGenerationContext):
        self.calls.append(ctx.task.model)
        return ctx.output_path, 0.0


# ── VideoModelDispatcher behavior ────────────────────────────────────────


def test_dispatcher_falls_back_to_default_when_no_route_matches():
    default = _FakeAdapter("default")
    d = VideoModelDispatcher(default_factory=lambda: default)
    assert d.resolve("wan2.6-i2v", "dashscope") is default


def test_dispatcher_routes_by_longest_prefix_match():
    default = _FakeAdapter("default")
    d = VideoModelDispatcher(default_factory=lambda: default)

    short = _FakeAdapter("short")
    long = _FakeAdapter("long")
    d.register("vidu", "vendor", lambda: short)
    d.register("viduq3", "vendor", lambda: long)

    assert d.resolve("viduq3-pro", "vendor") is long
    assert d.resolve("vidu-1.5", "vendor") is short


def test_dispatcher_caches_adapter_instances():
    default = _FakeAdapter("default")
    d = VideoModelDispatcher(default_factory=lambda: default)

    created = []

    def factory():
        adapter = _FakeAdapter("kling")
        created.append(adapter)
        return adapter

    d.register("kling-", "vendor", factory)
    a = d.resolve("kling-v3", "vendor")
    b = d.resolve("kling-v2", "vendor")
    assert a is b  # cache hit
    assert len(created) == 1


def test_dispatcher_distinguishes_backends_for_same_family():
    default = _FakeAdapter("default")
    d = VideoModelDispatcher(default_factory=lambda: default)

    vendor = _FakeAdapter("vendor")
    d.register("kling-", "vendor", lambda: vendor)

    assert d.resolve("kling-v3", "vendor") is vendor
    # dashscope has no registration → default
    assert d.resolve("kling-v3", "dashscope") is default


def test_dispatcher_register_rejects_invalid_inputs():
    d = VideoModelDispatcher(default_factory=lambda: _FakeAdapter("default"))
    with pytest.raises(ValueError):
        d.register("", "vendor", lambda: _FakeAdapter("x"))
    with pytest.raises(ValueError):
        d.register("kling-", "bogus", lambda: _FakeAdapter("x"))


# ── Default dispatcher composition ───────────────────────────────────────


def test_default_dispatcher_registers_all_vendor_routes():
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    routes = dict.fromkeys(d.list_routes(), True)
    expected = {
        ("kling-", "vendor"),
        ("vidu", "vendor"),
        ("viduq3", "vendor"),
        ("pixverse-", "vendor"),
        ("doubao-seedance-", "vendor"),
        ("hailuo-", "vendor"),
        ("minimax-hailuo-", "vendor"),
    }
    for r in expected:
        assert r in routes


def test_minimax_hailuo_model_resolves_to_real_adapter():
    """``MiniMax-Hailuo-2.3`` (canonical API id) must reach HailuoVendorAdapter,
    not the NotImplementedAdapter that used to live there."""
    from src.models.video_dispatcher import HailuoVendorAdapter

    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    adapter = d.resolve("MiniMax-Hailuo-2.3", "vendor")
    assert isinstance(adapter, HailuoVendorAdapter)
    adapter2 = d.resolve("hailuo-2.3-768p", "vendor")
    assert isinstance(adapter2, HailuoVendorAdapter)


def test_default_dispatcher_routes_dashscope_to_wanx_adapter():
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    adapter = d.resolve("wan2.6-i2v", "dashscope")
    assert isinstance(adapter, WanxDashScopeAdapter)


def test_default_dispatcher_routes_kling_vendor_to_kling_adapter():
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    adapter = d.resolve("kling-v3", "vendor")
    assert isinstance(adapter, KlingVendorAdapter)


def test_default_dispatcher_routes_vidu_vendor_to_vidu_adapter():
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    adapter = d.resolve("viduq3-pro", "vendor")
    assert isinstance(adapter, ViduVendorAdapter)


def test_preview_vendor_adapters_raise_clear_not_implemented():
    """Pixverse vendor-direct still has no client adapter — its dispatcher
    entry must raise a clearly-labelled NotImplementedError so a stale
    project state surfaces a readable error instead of falling through.

    (Doubao Seedance and Hailuo were promoted to real adapters in the
    2026-05 vendor expansion; they're covered by their own credential
    error paths instead of NotImplementedError.)"""
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    task = SimpleNamespace(
        model="pixverse-v4", prompt="x", duration=5, seed=None,
        resolution="720p", prompt_extend=False, negative_prompt="",
        shot_type=None, reference_video_urls=[], generation_mode="i2v",
        mode=None, sound=None, cfg_scale=None, vidu_audio=None, movement_amplitude=None,
    )
    adapter = d.resolve("pixverse-v4", "vendor")
    ctx = VideoGenerationContext(task=task, output_path="/tmp/out.mp4")
    with pytest.raises(NotImplementedError) as exc_info:
        adapter.generate(ctx)
    assert "pixverse" in str(exc_info.value).lower()


def test_doubao_seedance_vendor_adapter_calls_real_client():
    """The Seedance vendor-direct adapter dispatches to
    ``src.models.seedance.generate_seedance_video`` — verify the wiring
    by raising a credential error (the deepest reachable failure without
    network access)."""
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    task = SimpleNamespace(
        model="doubao-seedance-2.0-pro", prompt="x", duration=5, seed=None,
        resolution="720p", prompt_extend=False, negative_prompt="",
        shot_type=None, reference_video_urls=[], generation_mode="i2v",
        mode=None, sound=None, cfg_scale=None, vidu_audio=None, movement_amplitude=None,
    )
    adapter = d.resolve("doubao-seedance-2.0-pro", "vendor")
    ctx = VideoGenerationContext(task=task, output_path="/tmp/out.mp4")
    with pytest.raises(RuntimeError) as exc_info:
        adapter.generate(ctx)
    # Real client reached; missing creds is the expected first failure.
    assert "DOUBAO_API_KEY" in str(exc_info.value)


def test_veo_vendor_adapter_dispatches_to_real_client():
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    task = SimpleNamespace(
        model="veo-3.1", prompt="x", duration=8, seed=None,
        resolution="1080p", prompt_extend=False, negative_prompt="",
        shot_type=None, reference_video_urls=[], generation_mode="i2v",
        mode=None, sound=None, cfg_scale=None, vidu_audio=None, movement_amplitude=None,
    )
    adapter = d.resolve("veo-3.1", "vendor")
    ctx = VideoGenerationContext(task=task, output_path="/tmp/out.mp4")
    with pytest.raises(RuntimeError) as exc_info:
        adapter.generate(ctx)
    assert "GOOGLE_API_KEY" in str(exc_info.value)


def test_fal_vendor_adapter_dispatches_to_real_client():
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    task = SimpleNamespace(
        model="fal-veo-3.1", prompt="x", duration=5, seed=None,
        resolution="720p", prompt_extend=False, negative_prompt="",
        shot_type=None, reference_video_urls=[], generation_mode="i2v",
        mode=None, sound=None, cfg_scale=None, vidu_audio=None, movement_amplitude=None,
    )
    adapter = d.resolve("fal-veo-3.1", "vendor")
    ctx = VideoGenerationContext(task=task, output_path="/tmp/out.mp4")
    with pytest.raises(RuntimeError) as exc_info:
        adapter.generate(ctx)
    assert "FAL_API_KEY" in str(exc_info.value)
