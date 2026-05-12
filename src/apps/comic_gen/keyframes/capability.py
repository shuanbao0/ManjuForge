"""Vendor → grid capability registry.

A central place to answer "can this T2I vendor render an NxM panel
composite in one call?" Keeping it in one module means adding support
for a new grid-native model (Nano Banana Pro, future FLUX grid, etc.)
is a one-line registry change rather than a sprinkle of if/elif across
the pipeline.

Default is "not capable" — unknown vendors fall through to per-shot
generation, which always works.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


@dataclass(frozen=True)
class GridCapability:
    """What grid layouts a vendor can produce in one composite call.

    ``supports_native_grid`` is the master switch; even when True, the
    caller must respect ``max_panels`` and (optionally)
    ``recommended_composite_size`` to stay within the vendor's quality
    envelope.
    """

    supports_native_grid: bool
    max_panels: int = 0
    recommended_composite_size: str = "1024*1024"

    @property
    def disabled(self) -> bool:
        return not self.supports_native_grid


# ── Registry ──────────────────────────────────────────────────────────
# Conservative defaults. Seedream is the only vendor that today renders
# 9-panel grids with consistent character/style. Add new vendors here
# only after empirically confirming consistency at the claimed panel
# count — false positives produce visually-broken output that the user
# blames on the pipeline, not on the model.

_REGISTRY: Dict[str, GridCapability] = {
    "doubao": GridCapability(
        supports_native_grid=True,
        max_panels=9,
        recommended_composite_size="2048*2048",
    ),
}


class _GridCapableVendorsView:
    """Live view over :data:`_REGISTRY` — ``"id" in view`` always
    reflects the current registry, even after :func:`register_capability`
    extends it at runtime. A frozenset snapshot would silently go stale
    on callers that imported it once at module load.
    """

    __slots__ = ()

    def __contains__(self, vendor_id: object) -> bool:
        if not isinstance(vendor_id, str):
            return False
        cap = _REGISTRY.get(vendor_id)
        return cap is not None and cap.supports_native_grid

    def __iter__(self):
        return iter(
            vid for vid, cap in _REGISTRY.items() if cap.supports_native_grid
        )

    def __repr__(self) -> str:
        return f"<GridCapableVendors {sorted(self)!r}>"


# Public name kept stable for callers that read it via membership tests.
GRID_CAPABLE_VENDORS = _GridCapableVendorsView()


_FALLBACK = GridCapability(supports_native_grid=False, max_panels=0)


def get_grid_capability(vendor_id: str | None) -> GridCapability:
    """Return the capability for ``vendor_id``; unknown → not capable."""
    if not vendor_id:
        return _FALLBACK
    return _REGISTRY.get(vendor_id, _FALLBACK)


def register_capability(vendor_id: str, capability: GridCapability) -> None:
    """Test/extension hook: add or replace a vendor capability."""
    _REGISTRY[vendor_id] = capability


def registered_vendors() -> Iterable[str]:
    return tuple(_REGISTRY)


__all__ = [
    "GridCapability",
    "GRID_CAPABLE_VENDORS",
    "get_grid_capability",
    "register_capability",
    "registered_vendors",
]
