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
    }
    for r in expected:
        assert r in routes


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
    video_generator = SimpleNamespace(model=None)
    d = build_default_dispatcher(video_generator)
    task = SimpleNamespace(
        model="doubao-seedance-1.0-pro", prompt="x", duration=5, seed=None,
        resolution="720p", prompt_extend=False, negative_prompt="",
        shot_type=None, reference_video_urls=[], generation_mode="i2v",
        mode=None, sound=None, cfg_scale=None, vidu_audio=None, movement_amplitude=None,
    )
    adapter = d.resolve("doubao-seedance-1.0-pro", "vendor")
    ctx = VideoGenerationContext(task=task, output_path="/tmp/out.mp4")
    with pytest.raises(NotImplementedError) as exc_info:
        adapter.generate(ctx)
    assert "doubao" in str(exc_info.value).lower()
