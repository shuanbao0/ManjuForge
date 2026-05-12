"""Keyframe-mode strategies.

Each :class:`KeyframeMode` decides four things for a batch keyframe job:

1. ``panels_per_frame`` — how many composite panels each storyboard
   frame consumes (1 for FirstFrame, 2 for FirstLast, N for MultiRef).
2. ``build_composite_prompt`` — how to phrase the grid prompt fed to
   the grid-capable T2I vendor.
3. ``tiles_to_assignments`` — how to map split tiles back to frames
   (in row-major panel order).
4. ``tile_slot`` — which storage slot on the frame each panel goes to
   (``main`` → ``rendered_image_asset``, ``end_frame`` →
   ``end_frame_asset``, ``ref`` → variants pool of
   ``rendered_image_asset``).

Strategy + Registry: adding a new mode is one class + a
:func:`register_mode` call; the pipeline orchestration doesn't change.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Protocol, Type

from ..models import StoryboardFrame


# ── Storage slots ─────────────────────────────────────────────────────
# Three slots covering all current modes. Pipeline owns the mapping
# slot → field; modes only declare which slot a given panel belongs in.

SLOT_MAIN = "main"
SLOT_END_FRAME = "end_frame"
SLOT_REF = "ref"


class KeyframeMode(Protocol):
    """Pluggable batch-keyframe layout strategy."""

    name: str

    def panels_per_frame(self) -> int:  # pragma: no cover - protocol
        ...

    def build_composite_prompt(
        self,
        frames: List[StoryboardFrame],
        style_prompt: str,
    ) -> str:  # pragma: no cover - protocol
        ...

    def tiles_to_assignments(
        self,
        tile_paths: List[str],
        frames: List[StoryboardFrame],
    ) -> Dict[str, List[str]]:  # pragma: no cover - protocol
        ...

    def tile_slot(self, panel_index: int) -> str:  # pragma: no cover - protocol
        ...


# ── Helpers ───────────────────────────────────────────────────────────


def _frame_description(frame: StoryboardFrame) -> str:
    """Compact one-line description used in composite prompts."""
    atmos = frame.visual_atmosphere or ""
    action = frame.action_description or ""
    if atmos and action:
        return f"{atmos}，{action}"
    return atmos or action or ""


def _composite_header(panel_count: int, style_prompt: str) -> str:
    style = style_prompt or "电影感写实"
    return (
        f"生成一张 {panel_count} 格的网格拼接图,从左到右、从上到下依次为 "
        f"Panel 1 到 Panel {panel_count}。\n"
        f"所有格子共用相同的画风、镜头质感、色调:{style}.\n"
        "每格独立成画,格与格之间留极细分隔线,严格按指定数量出格,不要合并、不要缺格。\n\n"
    )


# ── FirstFrameMode ─────────────────────────────────────────────────────


@dataclass
class FirstFrameMode:
    """One panel per frame — the opening composition of each shot.

    Default and most-used mode: 9 frames → one 3×3 grid → 9 single-tile
    keyframes. Cheapest in tokens and easiest for the model to keep
    consistent style across panels.
    """

    name: str = "first_frame"

    def panels_per_frame(self) -> int:
        return 1

    def build_composite_prompt(
        self,
        frames: List[StoryboardFrame],
        style_prompt: str,
    ) -> str:
        body_lines = [
            f"Panel {i}: {_frame_description(f)}".strip()
            for i, f in enumerate(frames, start=1)
        ]
        return _composite_header(len(frames), style_prompt) + "\n".join(body_lines)

    def tiles_to_assignments(
        self,
        tile_paths: List[str],
        frames: List[StoryboardFrame],
    ) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for i, frame in enumerate(frames):
            if i >= len(tile_paths):
                break
            out[frame.id] = [tile_paths[i]]
        return out

    def tile_slot(self, panel_index: int) -> str:
        return SLOT_MAIN


# ── FirstLastMode ──────────────────────────────────────────────────────


@dataclass
class FirstLastMode:
    """Two panels per frame — opening + closing keyframes.

    Designed for i2v backends that accept a start+end frame pair
    (Wan 2.2 i2v, Kling multi-shot): the first tile drops into
    ``rendered_image_asset`` (canonical seed), the second into
    ``end_frame_asset`` (closing keyframe). At Seedream's 9-panel
    cap, this covers up to 4 frames per batch (8 tiles + 1 blank).
    """

    name: str = "first_last"

    def panels_per_frame(self) -> int:
        return 2

    def build_composite_prompt(
        self,
        frames: List[StoryboardFrame],
        style_prompt: str,
    ) -> str:
        n_panels = len(frames) * 2
        lines = []
        for i, f in enumerate(frames, start=1):
            desc = _frame_description(f)
            # Each frame gets a [opening, closing] pair; closing emphasises
            # the post-action state so the i2v model has a clear motion arc.
            lines.append(f"Panel {2*i - 1} (镜头 {i} 开场): {desc}")
            lines.append(
                f"Panel {2*i} (镜头 {i} 落幅): {desc} 完成后的最终画面状态,人物表情与肢体已稳定。"
            )
        return _composite_header(n_panels, style_prompt) + "\n".join(lines)

    def tiles_to_assignments(
        self,
        tile_paths: List[str],
        frames: List[StoryboardFrame],
    ) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for i, frame in enumerate(frames):
            first_idx = 2 * i
            last_idx = first_idx + 1
            if first_idx >= len(tile_paths):
                break
            pair = [tile_paths[first_idx]]
            if last_idx < len(tile_paths):
                pair.append(tile_paths[last_idx])
            out[frame.id] = pair
        return out

    def tile_slot(self, panel_index: int) -> str:
        """Panel 0 of each frame → main; panel 1 → end_frame."""
        return SLOT_MAIN if panel_index == 0 else SLOT_END_FRAME


# ── MultiRefMode ───────────────────────────────────────────────────────


@dataclass
class MultiRefMode:
    """N panels per frame — same shot from different angles/compositions.

    Use when you want a pool of alternative reference images for the
    same beat: e.g. 3 frames × 3 angles = 9 panels. All tiles land in
    ``rendered_image_asset.variants`` so the user can pick which angle
    becomes the seed for downstream i2v.

    ``panels`` defaults to 3 (max 3 frames per batch on Seedream's
    9-panel ceiling). Override by subclassing + register_mode if you
    need a different fan-out.
    """

    name: str = "multi_ref"
    panels: int = 3

    def panels_per_frame(self) -> int:
        return self.panels

    def build_composite_prompt(
        self,
        frames: List[StoryboardFrame],
        style_prompt: str,
    ) -> str:
        n_panels = len(frames) * self.panels
        # Angle hints rotate per panel-within-frame so the LLM gets
        # explicit variety direction rather than producing 3 nearly
        # identical tiles.
        angle_hints = ["正面平视", "侧面 45 度", "俯视角度", "仰视角度", "背面侧脸"]
        lines = []
        panel_idx = 0
        for f_idx, f in enumerate(frames, start=1):
            desc = _frame_description(f)
            for slot_idx in range(self.panels):
                panel_idx += 1
                angle = angle_hints[slot_idx % len(angle_hints)]
                lines.append(
                    f"Panel {panel_idx} (镜头 {f_idx} · {angle}): {desc}"
                )
        return _composite_header(n_panels, style_prompt) + "\n".join(lines)

    def tiles_to_assignments(
        self,
        tile_paths: List[str],
        frames: List[StoryboardFrame],
    ) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        cursor = 0
        for frame in frames:
            chunk = tile_paths[cursor : cursor + self.panels]
            if not chunk:
                break
            out[frame.id] = chunk
            cursor += self.panels
        return out

    def tile_slot(self, panel_index: int) -> str:
        return SLOT_REF


# ── Registry ──────────────────────────────────────────────────────────


_REGISTRY: Dict[str, Type[KeyframeMode]] = {
    FirstFrameMode().name: FirstFrameMode,
    FirstLastMode().name: FirstLastMode,
    MultiRefMode().name: MultiRefMode,
}


def register_mode(name: str) -> Callable[[Type[KeyframeMode]], Type[KeyframeMode]]:
    """Decorator: register a new mode class under ``name``."""

    def _wrap(cls: Type[KeyframeMode]) -> Type[KeyframeMode]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_mode(name: str, **kwargs: Any) -> KeyframeMode:
    """Instantiate a registered mode. ``kwargs`` are filtered to fields
    the mode's dataclass actually declares — unknown keys are dropped
    silently so callers can pass mode-specific extras without
    branching."""
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown keyframe mode {name!r}. Registered: {sorted(_REGISTRY)}"
        )
    cls = _REGISTRY[name]
    if dataclasses.is_dataclass(cls):
        allowed = {f.name for f in dataclasses.fields(cls)}
        safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    else:
        safe_kwargs = kwargs
    return cls(**safe_kwargs)


__all__ = [
    "KeyframeMode",
    "FirstFrameMode",
    "FirstLastMode",
    "MultiRefMode",
    "register_mode",
    "get_mode",
    "SLOT_MAIN",
    "SLOT_END_FRAME",
    "SLOT_REF",
]
