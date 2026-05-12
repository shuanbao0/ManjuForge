"""Tests for the batch-keyframe pipeline.

Three layers:

* ``capability``: vendor → grid capability registry, including the
  monkey-patch-friendly ``register_capability`` extension hook.
* ``splitter``: pure PIL math — pixel-aligned tile cropping.
* ``modes``: the FirstFrameMode strategy contract.
* ``pipeline``: ``batch_generate_frame_keyframes`` orchestration —
  routing decision, grid path, per-shot fallback.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.apps.comic_gen.keyframes import (
    FirstFrameMode,
    GRID_CAPABLE_VENDORS,
    GridCapability,
    GridLayout,
    get_grid_capability,
    get_mode,
    pick_layout,
    split_grid_image,
)
from src.apps.comic_gen.keyframes.capability import register_capability
from src.apps.comic_gen.models import (
    ArtDirection,
    Character,
    Scene,
    Script,
    StoryboardFrame,
)
from src.apps.comic_gen.pipeline import ComicGenPipeline


# ── Capability registry ───────────────────────────────────────────────


def test_doubao_is_grid_capable():
    cap = get_grid_capability("doubao")
    assert cap.supports_native_grid
    assert cap.max_panels == 9
    assert "doubao" in GRID_CAPABLE_VENDORS


def test_unknown_vendor_is_not_capable():
    cap = get_grid_capability("nonsense")
    assert not cap.supports_native_grid
    assert cap.max_panels == 0


def test_none_vendor_is_not_capable():
    """No active instance → no grid path."""
    cap = get_grid_capability(None)
    assert not cap.supports_native_grid


def test_register_capability_extension_hook():
    """Tests + future vendor adapters can opt into the grid path."""
    register_capability("nano_banana", GridCapability(True, max_panels=16))
    try:
        assert "nano_banana" in GRID_CAPABLE_VENDORS
        assert get_grid_capability("nano_banana").max_panels == 16
    finally:
        # Reset by re-registering as not-capable to avoid bleed across tests.
        register_capability("nano_banana", GridCapability(False, 0))


# ── Splitter ──────────────────────────────────────────────────────────


def _make_composite(tmp_path, w: int = 300, h: int = 300) -> str:
    """Create a solid-colour PNG so the splitter has real bytes to chew on."""
    path = str(tmp_path / "composite.png")
    Image.new("RGB", (w, h), color=(123, 45, 67)).save(path)
    return path


def test_pick_layout_known_counts():
    assert pick_layout(1) == GridLayout(1, 1)
    assert pick_layout(4) == GridLayout(2, 2)
    assert pick_layout(9) == GridLayout(3, 3)


def test_pick_layout_rejects_invalid():
    with pytest.raises(ValueError):
        pick_layout(0)
    with pytest.raises(ValueError):
        pick_layout(10)  # over max


def test_split_writes_row_major_tiles(tmp_path):
    composite = _make_composite(tmp_path, w=300, h=300)
    out_dir = str(tmp_path / "tiles")

    paths = split_grid_image(composite, rows=3, cols=3, out_dir=out_dir, basename="x")

    assert len(paths) == 9
    # Row-major ordering: filenames must end _0 through _8 in order
    for i, p in enumerate(paths):
        assert p.endswith(f"x_{i}.png")
        with Image.open(p) as tile:
            assert tile.size == (100, 100)


def test_split_rounds_down_on_non_divisible(tmp_path):
    """301x301 / 3x3 → tiles are 100x100; rightmost pixel column dropped."""
    composite = _make_composite(tmp_path, w=301, h=301)
    out_dir = str(tmp_path / "tiles")

    paths = split_grid_image(composite, rows=3, cols=3, out_dir=out_dir, basename="x")

    with Image.open(paths[0]) as tile:
        assert tile.size == (100, 100)


def test_split_raises_on_missing_image(tmp_path):
    with pytest.raises(FileNotFoundError):
        split_grid_image(
            str(tmp_path / "nope.png"), 2, 2, str(tmp_path), "x",
        )


def test_split_raises_on_too_small_composite(tmp_path):
    composite = _make_composite(tmp_path, w=2, h=2)
    with pytest.raises(ValueError, match="too small"):
        split_grid_image(composite, rows=3, cols=3, out_dir=str(tmp_path), basename="x")


# ── Modes ─────────────────────────────────────────────────────────────


def _frame(name: str, **kw) -> StoryboardFrame:
    return StoryboardFrame(
        id=kw.pop("id", str(uuid.uuid4())),
        scene_id=kw.pop("scene_id", "s1"),
        action_description=name,
        **kw,
    )


def test_first_frame_mode_panels_per_frame():
    assert FirstFrameMode().panels_per_frame() == 1


def test_first_frame_mode_prompt_lists_panels_in_order():
    frames = [_frame("A 翻身"), _frame("B 坐起"), _frame("C 走出门")]
    prompt = FirstFrameMode().build_composite_prompt(frames, "电影感写实")

    assert "3 格" in prompt
    assert "电影感写实" in prompt
    assert "Panel 1" in prompt and "A 翻身" in prompt
    assert "Panel 2" in prompt and "B 坐起" in prompt
    assert "Panel 3" in prompt and "C 走出门" in prompt
    # Style consistency instruction MUST be present — that's the
    # whole point of the grid mode.
    assert "共用相同的画风" in prompt


def test_first_frame_mode_assigns_tiles_in_order():
    frames = [_frame("A", id="f1"), _frame("B", id="f2"), _frame("C", id="f3")]
    tiles = ["/t/0.png", "/t/1.png", "/t/2.png"]

    out = FirstFrameMode().tiles_to_assignments(tiles, frames)

    assert out == {"f1": ["/t/0.png"], "f2": ["/t/1.png"], "f3": ["/t/2.png"]}


def test_first_frame_mode_drops_extra_tiles():
    """3 frames but splitter returned 4 tiles (e.g. 2x2 layout) — extras drop."""
    frames = [_frame("A", id="f1"), _frame("B", id="f2"), _frame("C", id="f3")]
    tiles = ["/t/0.png", "/t/1.png", "/t/2.png", "/t/3.png"]

    out = FirstFrameMode().tiles_to_assignments(tiles, frames)

    assert len(out) == 3
    assert "/t/3.png" not in [v[0] for v in out.values()]


def test_get_mode_registry():
    assert isinstance(get_mode("first_frame"), FirstFrameMode)
    with pytest.raises(ValueError, match="Unknown keyframe mode"):
        get_mode("invalid")


# ── Pipeline orchestration ────────────────────────────────────────────


@pytest.fixture
def pipeline_fx(tmp_path):
    with patch("src.apps.comic_gen.pipeline.ScriptProcessor"), \
         patch("src.apps.comic_gen.pipeline.AssetGenerator"), \
         patch("src.apps.comic_gen.pipeline.StoryboardGenerator"), \
         patch("src.apps.comic_gen.pipeline.VideoGenerator"), \
         patch("src.apps.comic_gen.pipeline.AudioGenerator"), \
         patch("src.apps.comic_gen.pipeline.ExportManager"):
        p = ComicGenPipeline()
    p.data_root = str(tmp_path)
    p.data_file = str(tmp_path / "projects.json")
    p.series_data_file = str(tmp_path / "series.json")
    p.scripts = {}
    p.series_store = {}
    return p


def _script_with_frames(n: int) -> Script:
    now = time.time()
    scene = Scene(id="s1", name="卧室", description="...")
    frames = [
        StoryboardFrame(
            id=f"f{i}", scene_id="s1",
            action_description=f"shot {i}",
            visual_atmosphere="昏暗",
        )
        for i in range(n)
    ]
    return Script(
        id="p1", title="Ep", original_text="...",
        scenes=[scene], frames=frames,
        created_at=now, updated_at=now,
    )


def test_pipeline_batch_picks_per_shot_when_vendor_not_grid_capable(pipeline_fx, tmp_path):
    """Default DashScope (no vendor_id) → per-shot path."""
    script = _script_with_frames(3)
    pipeline_fx.scripts[script.id] = script

    # StoryboardGenerator.generate_frame is mocked; emulate it writing
    # a rendered_image_asset on the frame.
    def fake_generate_frame(frame, characters, scene, **kw):
        from src.apps.comic_gen.models import ImageAsset, ImageVariant
        frame.rendered_image_asset = ImageAsset()
        v = ImageVariant(id="v1", url=f"storyboard/{frame.id}.png")
        frame.rendered_image_asset.variants.append(v)
        frame.rendered_image_asset.selected_id = "v1"
        return frame
    pipeline_fx.storyboard_generator.generate_frame.side_effect = fake_generate_frame

    result = pipeline_fx.batch_generate_frame_keyframes(
        script.id, ["f0", "f1", "f2"],
    )

    assert result["method"] == "per_shot"
    assert pipeline_fx.storyboard_generator.generate_frame.call_count == 3
    assert all(len(v) == 1 for v in result["assignments"].values())


def test_pipeline_batch_uses_grid_for_seedream(pipeline_fx, tmp_path):
    """Grid-capable vendor → one composite + split into N tiles."""
    script = _script_with_frames(4)
    pipeline_fx.scripts[script.id] = script

    # Fake the adapter to actually write a 200x200 PNG so the splitter has
    # real bytes — tests the full grid path including PIL I/O.
    def fake_generate(prompt, output_path, size=None, **kw):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        Image.new("RGB", (200, 200), color=(10, 20, 30)).save(output_path)
        return (output_path, 0.1)
    fake_adapter = MagicMock()
    fake_adapter.generate.side_effect = fake_generate
    pipeline_fx.storyboard_generator._route_for_call.return_value = fake_adapter

    # Fake the active T2I instance to vendor_id=doubao.
    fake_inst = MagicMock(vendor_id="doubao")
    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = fake_inst
        scoped.return_value.__exit__.return_value = False
        result = pipeline_fx.batch_generate_frame_keyframes(
            script.id, ["f0", "f1", "f2", "f3"],
        )

    assert result["method"] == "grid"
    assert result["vendor"] == "doubao"
    # One composite call, NOT per-shot
    assert fake_adapter.generate.call_count == 1
    # Each frame got one tile
    for fid in ["f0", "f1", "f2", "f3"]:
        assert len(result["assignments"][fid]) == 1
    # Per-shot generator must NOT have been touched
    assert pipeline_fx.storyboard_generator.generate_frame.call_count == 0


def test_pipeline_batch_force_per_shot_bypasses_grid(pipeline_fx, tmp_path):
    """Even with Seedream, force_per_shot=True takes the fallback path."""
    script = _script_with_frames(2)
    pipeline_fx.scripts[script.id] = script
    pipeline_fx.storyboard_generator.generate_frame.return_value = None

    fake_inst = MagicMock(vendor_id="doubao")
    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = fake_inst
        scoped.return_value.__exit__.return_value = False
        result = pipeline_fx.batch_generate_frame_keyframes(
            script.id, ["f0", "f1"], force_per_shot=True,
        )

    assert result["method"] == "per_shot"


def test_pipeline_batch_raises_on_missing_frames(pipeline_fx):
    script = _script_with_frames(2)
    pipeline_fx.scripts[script.id] = script

    with pytest.raises(ValueError, match="Frames not found"):
        pipeline_fx.batch_generate_frame_keyframes(script.id, ["f0", "nope"])


def test_pipeline_batch_raises_on_empty_request(pipeline_fx):
    script = _script_with_frames(1)
    pipeline_fx.scripts[script.id] = script

    with pytest.raises(ValueError, match="must not be empty"):
        pipeline_fx.batch_generate_frame_keyframes(script.id, [])


def test_pipeline_batch_falls_back_when_panel_count_exceeds_max(pipeline_fx):
    """Seedream max=9; 10 frames → fallback to per-shot."""
    script = _script_with_frames(10)
    pipeline_fx.scripts[script.id] = script
    pipeline_fx.storyboard_generator.generate_frame.return_value = None

    fake_inst = MagicMock(vendor_id="doubao")
    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = fake_inst
        scoped.return_value.__exit__.return_value = False
        result = pipeline_fx.batch_generate_frame_keyframes(
            script.id, [f"f{i}" for i in range(10)],
        )

    assert result["method"] == "per_shot"


def test_pipeline_batch_single_frame_takes_per_shot_path(pipeline_fx):
    """A single-frame batch has no grid benefit — go per-shot even on Seedream."""
    script = _script_with_frames(1)
    pipeline_fx.scripts[script.id] = script
    pipeline_fx.storyboard_generator.generate_frame.return_value = None

    fake_inst = MagicMock(vendor_id="doubao")
    with patch("src.apps.comic_gen.pipeline.scoped_instance") as scoped:
        scoped.return_value.__enter__.return_value = fake_inst
        scoped.return_value.__exit__.return_value = False
        result = pipeline_fx.batch_generate_frame_keyframes(script.id, ["f0"])

    assert result["method"] == "per_shot"
