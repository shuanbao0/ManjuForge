"""Keyframe-mode strategies.

Each :class:`KeyframeMode` decides three things for a batch keyframe
job:

1. How many panels each storyboard frame consumes
   (``panels_per_frame``).
2. How to phrase the composite prompt fed to the grid-capable T2I
   vendor (``build_composite_prompt``).
3. How to map the split tiles back to frames
   (``tiles_to_assignments``).

This Strategy hand-off keeps the orchestration code in ``pipeline.py``
mode-agnostic — adding a new mode (first-last keyframe pair,
multi-angle reference grid, etc.) is a new class + one
:func:`register_mode` call, no pipeline changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Protocol, Type

from ..models import StoryboardFrame


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
        n = len(frames)
        # Header instructs the model to lay panels out in row-major order
        # and keep style consistent across them. The per-panel block
        # carries each frame's specific visual description.
        header = (
            f"生成一张 {n} 格的网格拼接图,从左到右、从上到下依次为 Panel 1 到 Panel {n}。\n"
            f"所有格子共用相同的画风、镜头质感、色调:{style_prompt or '电影感写实'}.\n"
            "每格独立成画,格与格之间留极细分隔线,严格按指定数量出格,不要合并、不要缺格。\n\n"
        )
        body_lines = []
        for i, f in enumerate(frames, start=1):
            atmos = f.visual_atmosphere or ""
            action = f.action_description or ""
            body_lines.append(
                f"Panel {i}: {atmos + '，' if atmos else ''}{action}".strip()
            )
        return header + "\n".join(body_lines)

    def tiles_to_assignments(
        self,
        tile_paths: List[str],
        frames: List[StoryboardFrame],
    ) -> Dict[str, List[str]]:
        """Map row-major tile index ``i`` → ``frames[i].id``.

        When the splitter returns more tiles than frames (because we
        picked a 3×3 layout for 7 frames), the extra tiles are
        silently dropped — they're blank padding from the model.
        """
        out: Dict[str, List[str]] = {}
        for i, frame in enumerate(frames):
            if i >= len(tile_paths):
                break
            out[frame.id] = [tile_paths[i]]
        return out


# ── Registry ──────────────────────────────────────────────────────────


_REGISTRY: Dict[str, Type[KeyframeMode]] = {
    FirstFrameMode().name: FirstFrameMode,
}


def register_mode(name: str) -> Callable[[Type[KeyframeMode]], Type[KeyframeMode]]:
    """Decorator: register a new mode class under ``name``."""

    def _wrap(cls: Type[KeyframeMode]) -> Type[KeyframeMode]:
        _REGISTRY[name] = cls
        return cls

    return _wrap


def get_mode(name: str) -> KeyframeMode:
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown keyframe mode {name!r}. Registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]()


__all__ = [
    "KeyframeMode",
    "FirstFrameMode",
    "register_mode",
    "get_mode",
]
