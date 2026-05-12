"""Per-entity equality rules — *Specification* pattern.

Each ``MatchSpec`` answers a single question:

    "Is this dict the LLM just emitted the same entity as
    one we already have?"

Splitting the rule per entity type keeps :class:`EntityCatalog`'s
``upsert_*`` methods free of nested if/elif chains and makes the
matching logic individually testable. Adding a new entity type means
adding one more spec class — not modifying existing ones.
"""
from __future__ import annotations

from typing import Any, Dict, Protocol, TypeVar

from ..models import Character, Prop, Scene


def _norm(s: Any) -> str:
    """Whitespace + case-insensitive normalisation for name comparison.

    LLMs frequently emit "叶 墨" / "叶墨 " / "Ye Mo" for what the catalog
    stores as "叶墨" — collapse those into the same key.
    """
    if s is None:
        return ""
    return "".join(str(s).split()).lower()


def _gender_conflict(existing: Any, candidate: Any) -> bool:
    """Treat blank/unknown as compatible; only true gender disagreement
    blocks a match. Prevents the "two 叶墨, one male one female" bug
    when the LLM gets gender wrong on one of two passes."""
    if not existing or not candidate:
        return False
    return _norm(existing) != _norm(candidate)


T = TypeVar("T")


class MatchSpec(Protocol):
    """Decide whether ``candidate`` refers to ``existing``."""

    def is_same(self, existing: T, candidate: Dict[str, Any]) -> bool:  # pragma: no cover - protocol
        ...


class CharacterMatchSpec:
    """Same character ⇔ same name AND no hard gender conflict."""

    def is_same(self, existing: Character, candidate: Dict[str, Any]) -> bool:
        if _norm(existing.name) != _norm(candidate.get("name")):
            return False
        return not _gender_conflict(existing.gender, candidate.get("gender"))


class SceneMatchSpec:
    """Same scene ⇔ same name AND compatible time_of_day.

    "卧室·白天" and "卧室·夜晚" are different shots, so they should
    not collapse — but if the LLM omits ``time_of_day`` on one side
    we still match (don't fragment the catalog on missing metadata).
    """

    def is_same(self, existing: Scene, candidate: Dict[str, Any]) -> bool:
        if _norm(existing.name) != _norm(candidate.get("name")):
            return False
        ex_tod = _norm(existing.time_of_day)
        cand_tod = _norm(candidate.get("time_of_day"))
        if ex_tod and cand_tod and ex_tod != cand_tod:
            return False
        return True


class PropMatchSpec:
    """Same prop ⇔ same name."""

    def is_same(self, existing: Prop, candidate: Dict[str, Any]) -> bool:
        return _norm(existing.name) == _norm(candidate.get("name"))


__all__ = [
    "MatchSpec",
    "CharacterMatchSpec",
    "SceneMatchSpec",
    "PropMatchSpec",
]
