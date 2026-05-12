"""Batch keyframe generation with vendor-aware grid composition.

Some image models (notably ByteDance Seedream 5.0 and Nano Banana Pro)
can render N consistent panels in a single composite image. That cuts
N round-trips to one and yields better cross-shot consistency than
calling per-shot generation N times.

ManjuForge's older models (Wan / FLUX.2 / Gemini Image / GPT Image)
don't render coherent grids natively. This package detects which path
a given user's active T2I instance supports and:

* uses native grid composition when the vendor advertises it
  (Seedream today; extendable via :mod:`capability`),
* falls back to per-shot parallel generation otherwise.

The public surface is :func:`get_grid_capability`,
:func:`split_grid_image`, and :class:`FirstFrameMode` — the orchestration
itself lives on ``ComicGenPipeline.batch_generate_frame_keyframes`` so it
shares the existing instance/transaction plumbing.
"""
from .capability import GRID_CAPABLE_VENDORS, GridCapability, get_grid_capability
from .modes import FirstFrameMode, KeyframeMode, get_mode, register_mode
from .splitter import GridLayout, pick_layout, split_grid_image

__all__ = [
    "GridCapability",
    "GRID_CAPABLE_VENDORS",
    "get_grid_capability",
    "GridLayout",
    "pick_layout",
    "split_grid_image",
    "KeyframeMode",
    "FirstFrameMode",
    "get_mode",
    "register_mode",
]
