"""Composite-image grid splitter (pure PIL utility).

Given a single image that a grid-capable T2I vendor returned, this
module crops it into ``rows * cols`` tiles in row-major order and
writes each tile to disk under ``out_dir`` with a sequential filename.

Keeping the splitter as a free function (no class, no state) makes it
trivially testable and reusable from anywhere — pipeline, tests, ad-hoc
scripts.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

from PIL import Image


@dataclass(frozen=True)
class GridLayout:
    """Result of :func:`pick_layout` — how to arrange ``panel_count``
    tiles into a rectangle."""

    rows: int
    cols: int

    @property
    def total(self) -> int:
        return self.rows * self.cols


# Pre-defined layouts in the order we prefer for each panel count.
# Square-ish layouts come first because Seedream renders them more
# evenly than tall/wide aspect ratios (its training data skews square).
_LAYOUT_TABLE: dict[int, Tuple[int, int]] = {
    1: (1, 1),
    2: (1, 2),
    3: (1, 3),
    4: (2, 2),
    5: (2, 3),   # 6 cells, 1 left blank (caller should pad)
    6: (2, 3),
    7: (3, 3),   # 9 cells, 2 left blank
    8: (3, 3),
    9: (3, 3),
}


def pick_layout(panel_count: int) -> GridLayout:
    """Pick a rows × cols layout that fits ``panel_count`` panels.

    Raises ``ValueError`` for ``panel_count <= 0`` or beyond the
    supported max (9). Higher counts would push individual tile
    resolution below useful quality on current models.
    """
    if panel_count <= 0:
        raise ValueError(f"panel_count must be positive, got {panel_count}")
    if panel_count not in _LAYOUT_TABLE:
        raise ValueError(
            f"panel_count={panel_count} not supported (max 9 — pick fewer frames)"
        )
    rows, cols = _LAYOUT_TABLE[panel_count]
    return GridLayout(rows=rows, cols=cols)


def split_grid_image(
    image_path: str,
    rows: int,
    cols: int,
    out_dir: str,
    basename: str,
) -> List[str]:
    """Crop ``image_path`` into ``rows × cols`` tiles and save under ``out_dir``.

    Tiles are written as ``{basename}_{i}.png`` where ``i`` is a
    row-major index starting at 0 (top-left). Returns the absolute
    paths in the same order. The output directory is created if
    missing; existing tile files with the same names are overwritten.

    The splitter rounds down on non-divisible dimensions so tiles stay
    pixel-aligned; up to ``cols-1`` pixels per row and ``rows-1`` per
    column may be dropped from the right/bottom edges. This is what
    every model that does grid composition expects callers to do.
    """
    if rows < 1 or cols < 1:
        raise ValueError(f"rows/cols must be ≥1 (got {rows}x{cols})")
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Composite image not found: {image_path}")

    os.makedirs(out_dir, exist_ok=True)
    paths: List[str] = []
    with Image.open(image_path) as img:
        img.load()  # decouple from the context manager before crop loop
        w, h = img.size
        tile_w, tile_h = w // cols, h // rows
        if tile_w == 0 or tile_h == 0:
            raise ValueError(
                f"Composite {w}x{h} too small for {rows}x{cols} grid"
            )
        for idx in range(rows * cols):
            r, c = divmod(idx, cols)
            box = (c * tile_w, r * tile_h, (c + 1) * tile_w, (r + 1) * tile_h)
            tile = img.crop(box)
            out_path = os.path.abspath(os.path.join(out_dir, f"{basename}_{idx}.png"))
            tile.save(out_path, format="PNG")
            paths.append(out_path)
    return paths


__all__ = ["GridLayout", "pick_layout", "split_grid_image"]
