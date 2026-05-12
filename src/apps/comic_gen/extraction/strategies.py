"""Extraction strategies — Strategy pattern.

The two shipped strategies differ only in how they treat the catalog:

* :class:`FullExtraction` ignores existing entities and re-emits
  everything (the legacy "single-shot script" behaviour).
* :class:`IncrementalExtraction` feeds the catalog summary back to the
  LLM and asks it to return ``match_id`` for any candidate that should
  reuse an existing entity — this is what makes Series episodes share
  characters/scenes/props without users having to dedupe by hand.

Both strategies return the same :class:`ExtractionResult`, so callers
can switch between them without changing downstream code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Protocol

from .catalog import EntityCatalog

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..llm import ScriptProcessor


@dataclass
class ExtractionResult:
    """Summary of one extraction pass.

    ``created_*`` lists IDs of brand-new catalog rows; ``reused_*`` lists
    IDs the LLM mapped onto existing rows. The two are disjoint, and
    their union is exactly the set of entities this episode references.
    """

    created_character_ids: List[str] = field(default_factory=list)
    reused_character_ids: List[str] = field(default_factory=list)
    created_scene_ids: List[str] = field(default_factory=list)
    reused_scene_ids: List[str] = field(default_factory=list)
    created_prop_ids: List[str] = field(default_factory=list)
    reused_prop_ids: List[str] = field(default_factory=list)

    @property
    def all_character_ids(self) -> List[str]:
        return self.created_character_ids + self.reused_character_ids

    @property
    def all_scene_ids(self) -> List[str]:
        return self.created_scene_ids + self.reused_scene_ids

    @property
    def all_prop_ids(self) -> List[str]:
        return self.created_prop_ids + self.reused_prop_ids


class ExtractionStrategy(Protocol):
    """Pluggable extraction algorithm."""

    name: str

    def extract(
        self,
        text: str,
        catalog: EntityCatalog,
        llm: "ScriptProcessor",
    ) -> ExtractionResult:  # pragma: no cover - protocol
        ...


# ── Concrete strategies ────────────────────────────────────────────────


class FullExtraction:
    """Legacy behaviour — always create new entities, never reuse.

    Useful for standalone scripts or when the user explicitly wants a
    clean slate. Catalog is treated as write-only: every candidate gets
    a fresh ID (modulo the catalog's own dedup safety net, which still
    catches exact-name collisions).
    """

    name = "full"

    def extract(
        self,
        text: str,
        catalog: EntityCatalog,
        llm: "ScriptProcessor",
    ) -> ExtractionResult:
        raw = llm.extract_entities(text, existing=None)
        return _apply_to_catalog(raw, catalog)


class IncrementalExtraction:
    """Incremental — feed catalog back, let LLM return ``match_id`` for reuse.

    This is the recommended path for Series episodes: the LLM sees what
    already exists (just names, gender, time_of_day — enough to match)
    and is instructed to *prefer reusing* known IDs over inventing new
    ones. Anything it does invent is new; anything it tags with a
    ``match_id`` is treated as a reference into the existing catalog.

    A safety net runs the per-entity ``MatchSpec`` on every "new"
    candidate as well — so even if the LLM misses a reuse opportunity,
    the catalog's deterministic rules catch it before a duplicate row
    is appended.
    """

    name = "incremental"

    def extract(
        self,
        text: str,
        catalog: EntityCatalog,
        llm: "ScriptProcessor",
    ) -> ExtractionResult:
        existing_summary = catalog.summary_for_llm()
        raw = llm.extract_entities(text, existing=existing_summary)
        return _apply_to_catalog(raw, catalog, existing_summary=existing_summary)


# ── Shared helper: write raw LLM dict into the catalog ──────────────────


def _apply_to_catalog(
    raw: Dict[str, Any],
    catalog: EntityCatalog,
    existing_summary: Dict[str, Any] | None = None,
) -> ExtractionResult:
    """Apply a raw LLM extraction dict to the catalog.

    Shape of ``raw``::

        {
          "characters": [
            {"name": "叶墨", "match_id": "char-uuid-or-null", "gender": "男", ...},
            ...
          ],
          "scenes": [...],
          "props": [...]
        }

    ``match_id`` is honoured first; if missing or stale, the catalog's
    ``upsert_*`` is called and its own ``MatchSpec`` either matches an
    existing row or appends a new one.
    """
    result = ExtractionResult()
    known_char_ids = {c["id"] for c in (existing_summary or {}).get("characters", [])}
    known_scene_ids = {s["id"] for s in (existing_summary or {}).get("scenes", [])}
    known_prop_ids = {p["id"] for p in (existing_summary or {}).get("props", [])}

    for cand in raw.get("characters", []) or []:
        match_id = cand.get("match_id")
        if match_id and match_id in known_char_ids:
            result.reused_character_ids.append(match_id)
            continue
        entity, created = catalog.upsert_character(cand)
        (result.created_character_ids if created else result.reused_character_ids).append(entity.id)

    for cand in raw.get("scenes", []) or []:
        match_id = cand.get("match_id")
        if match_id and match_id in known_scene_ids:
            result.reused_scene_ids.append(match_id)
            continue
        entity, created = catalog.upsert_scene(cand)
        (result.created_scene_ids if created else result.reused_scene_ids).append(entity.id)

    for cand in raw.get("props", []) or []:
        match_id = cand.get("match_id")
        if match_id and match_id in known_prop_ids:
            result.reused_prop_ids.append(match_id)
            continue
        entity, created = catalog.upsert_prop(cand)
        (result.created_prop_ids if created else result.reused_prop_ids).append(entity.id)

    catalog.link_to_episode(
        character_ids=result.all_character_ids,
        scene_ids=result.all_scene_ids,
        prop_ids=result.all_prop_ids,
    )
    return result


__all__ = [
    "ExtractionResult",
    "ExtractionStrategy",
    "FullExtraction",
    "IncrementalExtraction",
]
